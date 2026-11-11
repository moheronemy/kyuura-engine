# 検証用 AI の次の小規模バッチの計画（計画の形式 3）

- 状態: **C1・C2 を採用して実行した（10 章）。その結果の 3 点を確認した（11 章。新しい対戦なし）**。1〜9 章は実行の前に書いた計画のまま（そのときは対戦・テスト・ビルド・seed の探索をせず、コード・文書・保存済みの証跡の読み取りとテキストの検索だけで調べた）。
- 基点: `claude/vai-p6-accepted` の `8531071`（実装 `c303da6`）。`origin/main`（`7b3d53c`）には未取り込み（`git merge-base --is-ancestor 8531071 origin/main` が 1）。
  配布の確かめ済みのコミット `4b6e3fe` から `8531071` まで、`kyuura_engine/` の差分はない。
- ブランチ: `claude/vai-batch-plan3`（文書だけ）。
- 目的: 局数を増やすことではなく、これまで届いていない操作・入力・結果へ範囲を広げること。

## 1. 今の到達範囲

### 1.1 根拠の区分

| 区分 | 中身 | 主な根拠 |
|---|---|---|
| (a) new_game から、ランダム・ルール・混合の方策で到達 | 固定デッキ第1版 1 組（`hitmonchan-dewgong` 対 `venusaur-parasect`）・`CS-KYUURA-CURRENT@1` だけ。30 局（`vai-batch-b1`）・99 局（`vai-batch-b2`）と、V0〜V3-1・v2_repeat の小さな対戦。0.176〜0.179 の追従は、その小さな対戦の再生・契約の比べ（移行の確かめ）で、新しい自然な対戦ではない | [verification-ai-batch.md](verification-ai-batch.md) 5 章・13 章、`vai-0176-follow`〜`vai-0179-follow` |
| (b) new_game から、固定の選び手による合法な操作の列で到達 | V3-2 のカツラの到達例（`BLAINE_DECK`・seed 1。2 局は固定の選び手、1 局は boundary）。エンジンのテストの U7 の接続（ラッキースタジアムの `play_trainer` → `use_stadium`。`tests/test_legal_actions_u7_5d.py:398-440`）。ニンジャジムの合法な列（`tests/test_ninja_gym_oracle_v0_146.py`） | [verification-ai-v3-2.md](verification-ai-v3-2.md)、エンジンのテスト |
| (c) 構築盤面だけ | P6（`p6-ai-follow`・`vai-p6-accepted`。受理の中身の判定の接続の証跡で、fixture を動かし直したもの。新しい自然な対戦ではない）・U-R3a（`u-r3a-ai-follow`）・PT-5e（`pt5e-v0.176`）・UP-5t-C1（`up5t-c1`）・PT-5t-C1（`pt5t-c1`）・V3-3 | 各文書。どれも「new_game からの到達ではない」と記録している |
| (d) 模擬の応答・単体テストだけ | 計画の形式・停止方針・集計（偽物の adapter）、P6・U-R3a の契約の小さな JSON の例、PT-5e の from_state の不変条件（テストの中の状態の編集でだけ作れる） | `tests/test_verification_ai_*` |
| 静的な監査だけ | UP-5t の監査・UP-5t D のトレーナーの監査（ねむれ!ねむれ! PMCG4-054・トロピカルウインド PR1-074 は実行の証跡がない） | [legal-actions-up5t-d-trainer-audit.md](legal-actions-up5t-d-trainer-audit.md) |
| エンジンの側の決まった手順の対戦（クライアント API・検証用 AI ではない） | 固定デッキ第2版の比べ（`tools/preset_deck_comparison.py`）、マチスの秘策の 40 局（`--batch v0.67`。うらで出す 56 回・おもてにする 33 回。にげるでおもてにした記録はない） | [preset-decks-v0.26.md](preset-decks-v0.26.md)、[secret-plan-preflight-v0.67.md](secret-plan-preflight-v0.67.md) |

### 1.2 99 局で届いたもの・届かなかったもの

「提示された 14 種類すべて」は、この 1 組・この規約集合で**提示された**種類がすべて選択・受理まで進んだという意味です。API の全種類・全入力経路の網羅ではありません。

- **候補の種類**: API は、プレイヤー 18 種類とホスト 2 種類の、合計 20 種類です（`legal_actions.py:170-202`）。99 局で提示されたのは 14 種類でした。
- **一度も提示されなかった 6 種類**: `use_stadium`・`reveal_face_down`・`remove_disguise`・`discard_from_play`・`start_sudden_death`・`check_face_up_deck`（表示だけ）。
- **選んだ候補の処理可能性**: supported と may_stop_later だけでした。unverified は選んでいません（deep の範囲なので、unverified は範囲の中に候補がないときだけ選ぶ）。
- **結果**: 受理だけでした。拒否・check の invalid・断り（refusal）は 0 です。
- **場面と決定**: 場面は `actor_to_act` だけでした。決定は `select_pokemon`・`take_prize`・`promote_active` の 3 種類だけです。
- **入力**: `choose_option` と `choose_value` の 2 種類で、API の入力の種類と同じです。ただし、段の形は 1〜3 段でした。
- **範囲の外**:
  - 処理可能性 unresolved_ruling の play_trainer: 1922 回。trace の選べるものでは、きずぐすり PMCG1-071 とポケモンいれかえ PMCG1-073 です。停止のコードは trace に残っていません。
  - にげるの入力を作れないもの（`total_units_unreachable`）: 3741 回。
- **停止**: 準備の停止 `UNRESOLVED_MULLIGAN_COMPENSATION` が seed 2025 で 3 局ありました。new_game の時点の停止で、操作は 0 です。
- **受理の中身（P6・U-R3a）**: 0 件でした。読むだけで数えたところ、30 局・99 局の trace に P6 の送信も 0 件です。

### 1.3 未到達・未確認（今回の対象の候補）

- **うらのカード**:
  - マチスの秘策（PMCG5-093）。固定デッキにありません。
  - P6（うらのバトル場のにげる）、U-R3a（うらのカードの特殊能力）、`reveal_face_down`。
  - 構築盤面でだけ確かめています。
- **スタジアム**: `use_stadium` は、固定デッキにスタジアムがないので、検証用 AI では提示されたことがありません。
- **トレーナーと決定**:
  - 固定デッキ第2版にだけあるトレーナー（突風・パソコン通信・エネルギー回収・ポケモン交換おじさん・ポケモン育て屋さん）と、モンジャラ。
  - 検証用 AI では未実行です（エンジンの側の決まった手順の対戦だけ）。
- **選択・拒否・停止**:
  - unverified の選択（boundary）。
  - 正常な拒否。
  - 受理のあとの停止。
  - 規約集合 S2A・PO での続行。

## 2. 狙う範囲と、届く見込み

### 2.1 実行の条件の制約（今の道具で何ができるか）

| 制約 | 内容 | 影響 |
|---|---|---|
| デッキ | バッチは固定デッキの識別子だけを受け付ける（`batch.py` の `EngineAdapter.entry`・`deck_check` は `preset_deck`。`decklists` は計画で None に固定） | マチスの秘策・スタジアムの入った 60 枚は、**実装の変更なしではバッチに載らない** |
| 方式 | `MODES` は uniform-stage・uniform-tuple・rules-v1・rules-v2・mixed で、どれも profile deep | **boundary はバッチに載らない**。deep は unverified を範囲の中に候補があるときは選ばない（P6・U-R3a の候補は unverified）。対象へ届かせるために deep の範囲・方策の順位は変えない |
| 規約集合 | 1 つの計画に 1 つの規約集合 | 集合の比べは、計画を分ける |
| 時間の上限 | 次の局を始める条件は「残り ≥ `game_reserve_seconds`（150 秒）」で、CLI からは変えられない | 計画ごとの予算は「見込み + 150 秒」が要る。計画を増やすほど、10 分に収めにくい |

### 2.2 対象ごとの見込み

| 対象 | 今の道具で届くか | 見込みと前提 | 限界 |
|---|---|---|---|
| 第2版のトレーナー（突風・パソコン通信・エネルギー回収・ポケモン交換おじさん・ポケモン育て屋さん）と、そこから出る決定・入力 | **届く**（固定デッキ第2版。deep） | rules の優先順位は play_trainer が 5（ワザ 4 のあと・番の終わり 6 の前）で、均等・混合でも候補にあれば選ばれうる。育て屋さんは、その番の最初から場にいるたねと 2 進化が手札に要る（おたがいの最初の番は不可） | 候補の処理可能性・入力の公開（山札を探す段が `withheld` になるか）は、静的には確かめていない。実行して数える |
| 規約集合 S2A の続行（準備の切り直しの補償） | **届く見込み**（seed 2025 は、CURRENT では new_game の時点で止まる） | 停止は操作 0 で起き、方策によらない。S2A の `PC-SETUP-MULLIGAN-COUNT` の場面（`#initial-setup`）に当たれば、補償のあと進む | その場面に当たるか（両方の回と片方だけの回が両方あるか）は、静的には確かめていない。当たらなければ S2A でも同じコードで止まる |
| S2A のほかの続行規約（ねむりのコインの順・ポケモンチェックのきぜつの時点など） | 届くかもしれない | パラセクトのねむりはあるが、両方のバトル場がねむりになる場面は少ない | 少数局で起きなくても、起きないとは言えない |
| PO の続行規約 | **届かない** | ［ポイズンミスト］が固定デッキにない | 比べられるのは「場面がないとき S2A と同じに進むか」だけ（追加案） |
| マチスの秘策・`reveal_face_down`・うらのカードのワザ | 届かない（デッキが載らない） | 既存の 60 枚 `L67`（`tools/existing_effect_games.py:1254`）を使えば、おもてにすることは deep でも選ばれうる（`reveal_face_down` は P6 の構築盤面で may_stop_later だった。マチスの秘策の play_trainer の処理可能性は静的には確かめていない） | 実装の変更（デッキリスト）が要る |
| P6 | 届かない（deep） | マチスの秘策はベンチに出すので、バトル場へ移る（相手の突風・自分のポケモンいれかえ・きぜつのあとの交代）ことが先に要る。そのうえ候補は unverified | boundary とデッキリストの両方が要る。それでも少数局では届かないことがありうる |
| U-R3a | 届かない | `L67` のポケモン（ディグダ・エビワラー・ケーシィ・ユンゲラー）に特殊能力はない。うらにした本当のカードが特殊能力を持つ必要がある（例: フシギバナ → たねでないのでトラッシュ。たねで特殊能力を持つカード → 使った） | 新しい検証用のデッキの候補と boundary が要る |
| `use_stadium` | 届かない（デッキが載らない） | `use_stadium` は may_stop_later（supported にはならない）なので deep の範囲に入る。ラッキースタジアムのデッキ（`LUCKY_DECK`）・ニンジャジムのデッキに、合法な列の例がある | デッキリストの実装が要る |
| unverified の選択・正常な拒否・受理のあとの停止 | 届かない（deep） | 拒否は、unverified の候補を送る boundary で起きやすい（P6 の費用の不足など） | boundary が要る |

## 3. 推奨の計画（今の道具で実行できる。2 組・合計 54 局）

デッキの条件は 2 組です。どちらも既存の固定デッキで、デッキのデータは変えません。カード名・ID 別の戦略はランナーに加えません。

### 3.1 計画 C1: 固定デッキ第2版（新しいトレーナー・決定）

- **デッキ**: `hitmonchan-dewgong-v2` 対 `venusaur-parasect-v2`（`kyuura_engine/decks.py:89-133`。根拠は [preset-decks-v0.26.md](preset-decks-v0.26.md) 2 章・3 章）。
  - 登録済みのカードかは、テキストで確かめた。カード ID は `decks.py` の 1 か所にあり、固定デッキのテスト（`tests/test_preset_decks_v0_26.py`）が対象。
  - この計画のためにデッキの合法性の検査は実行していない。
- **規約集合**: `CS-KYUURA-CURRENT@1`（`sha256:9a9b95c6…3cee`）。
- **方式と seed**:
  - 方式: uniform-stage・rules-v2・mixed（ε 0.25）。
  - seed: 3001〜3009（今回事前に固定した。既存の計画と重ならない）。
  - 9 × 3 = **27 局**。
- **上限**: 予算 360 秒（次の局を始めるのは累積 210 秒まで）・証跡 640 MiB・単局の上限は既存の値（runner.Limits の既定）。

### 3.2 計画 C2: 規約集合 S2A（準備の停止の続行と、続行のない局の一致）

- **デッキ**: 第1版 `hitmonchan-dewgong` 対 `venusaur-parasect`（99 局と同じ）。
- **規約集合**: `CS-KYUURA-PLAY-S2A@1`（`sha256:b317a3f0…10c4`。開発用の部分的な集合）。
- **方式と seed**:
  - 方式: uniform-stage・rules-v2・mixed。
  - seed: 2025・2001〜2008 の 9 個 × 3 = **27 局**。
    - 2025 は、保存済みの 99 局で準備の停止が出た seed なので、結果を見て選んだ（停止の続行を比べるため、と明記する）。
    - 2001〜2008 は 99 局の計画の seed の先頭 8 個で、結果では選んでいない。
- **上限**: 予算 240 秒（次の局を始めるのは累積 90 秒まで）・証跡 384 MiB。
- **CURRENT との比べ**: 新しい対戦をせず、99 局の保存済みの局（同じ seed・方式）を使う。
  - エンジンは `4b6e3fe` から変わっていない。
  - runner の変更（`c303da6`）は P6・うらの特殊能力の受理の記録だけで、第1版の組では起きない。
  - 99 局の時点の行動の指紋の確かめ（v2_repeat の ACTION_GOLDEN）も、変更のあとで通っている。

### 3.3 予算の合計と見込み

| | 局 | 予算の上限 | 証跡の上限 | 見込み（参考） |
|---|---|---|---|---|
| C1 | 27 | 360 秒 | 640 MiB | 不明（第2版は探す・回収するトレーナーが多く、操作が増える可能性） |
| C2 | 27 | 240 秒 | 384 MiB | 99 局の 1 局 2.83 秒・5.2 MB から、約 76 秒・140 MB |
| 合計 | 54 | 600 秒（10 分） | 1024 MiB（1 GiB） | |

- **運用**: 単一のプロセスで、逐次に実行する。seed・全条件は、実行の前に計画（`plan.json`・`plan.sha256`）へ固定する。上限に達したら未着手を残して終わり、延長しない。
- **時間の見込み**: 1 局の時間は、99 局の中央値 1.66 秒・最大 19.2 秒が参考値。C1 は、累積 210 秒を超えると残りが未着手になる（それも結果として残す）。
- **メモリと証跡**: 最大 345 MB・1 局あたり約 5.2 MB は、第1版の組の参考値。デッキが変わると増える可能性がある。
- **旧バッチ**: 30 局・99 局は、元の道具の版（TOOL_VERSION 1・2）とともに残し、新しい版で再開・再集計しない。C1・C2 は計画の形式 3 の新しい計画。

### 3.4 停止方針（推奨の初期値。今の道具の既定と同じ）

| 区分 | 扱い |
|---|---|
| known_stop | 保存して続ける |
| 根拠不足の既知の停止（`evidence_missing_stop`） | 理由ごとに保存して続ける（`--undetermined-evidence-missing continue`） |
| `accepted_content_unrecorded` | 保存して止める |
| 未知の診断・契約の未知・no_progress・分類できない undetermined | 保存して止める |
| suspect・状態の不整合・failed・replay_run の不一致・書き込みの失敗 | 保存して止める |

- 停止の確かめ（`--acknowledge-stop`）は自動で外さない。
- 各局は、完全な記録・trace・判定（`judge.json`）・資源の記録を保存し、replay_run で確かめる（局の数に足さない）。
- 新しいデッキで不具合の候補が出たら、同じバッチをくり返さず、対象の局と根拠を保存して、最小の再現へ切り出す（別の作業）。

### 3.5 実行の前に記録すること

- **デッキ**: 内容の確認値（計画の `decks`。既存）と、`kyuura_engine.deck.deck_problems` の結果（合法性の検査）を、実行の前の記録として保存する。
  - バッチには合法性の検査の記録がないので、証跡の側の小さなスクリプトで記録する。new_game も同じ検査をする。
- **規約集合**: 識別（ID・版・確認値）は計画に入る（既存）。

## 4. 規約集合の比べ

| 集合 | ID・版・確認値 | 中身 |
|---|---|---|
| 既定 | `CS-KYUURA-CURRENT@1`・`sha256:9a9b95c6…3cee` | 今の挙動。記録で決まらない場面は `UNRESOLVED_…` で止める（strict） |
| S2A | `CS-KYUURA-PLAY-S2A@1`・`sha256:b317a3f0…10c4` | 既定の 12 規約 + S2a の続行規約 5 件（準備の切り直しの回の数え方・ポケモンとして出せるトレーナー・ねむり/くろこげのコインの順・コインの数の不足・ポケモンチェックのきぜつの時点）。開発用の部分的な集合で、ほかの場面は止める |
| PO | `CS-KYUURA-PLAY-PO@1`・`sha256:06d51219…3528` | S2A + ［ポイズンミスト］とどくの量の続行規約 3 件 |

| 比べ | 期待する差 | 不具合の候補 |
|---|---|---|
| seed 2025: 既定（99 局の保存済み）と S2A（C2） | 既定は new_game の時点で `UNRESOLVED_MULLIGAN_COMPENSATION`。S2A は `convention_applied`（`PC-SETUP-MULLIGAN-COUNT`）のあと補償の決定を経て進む | S2A で、続行規約を当てずに進む。または同じ場面で別のコードで止まる。場面に当たらず同じコードで止まるのは、不具合ではなく「場面の外」として記録する |
| seed 2001〜2008: 既定（99 局）と S2A（C2） | `convention_applied` が起きない局は、操作の列の指紋（`sequences.json`）が同じ。起きた局は、その時点から先が変わってよい | `convention_applied` のない局で指紋が違う |
| PO と S2A（追加案 1） | 固定デッキに［ポイズンミスト］がないので、同じ seed・方式で同じ | PO の場面のない局で違う |

- **因果の読み方**: 同じ seed でも、集合・方策によって操作の列と乱数の消費が変わる。続行規約が当たったあとの結果の差（勝敗・番の数）を、その規約の因果的な効果と断定しない。
- **停止を解除しない**: 既定（strict）の停止は既知の停止で、完走のために解除しない。S2A の続行は、利用者が採用した続行規約による進行で、strict の停止とは区別して数える。
- **集計の不足**: `convention_applied` の件数は、バッチの集計に入っていない。比べは、保存した記録のログを読むだけのスクリプトで行う（実装の候補。6 章）。

## 5. 成果の測り方

### 5.1 対応表

段階は、提示（offered）・範囲（in_scope）・選択（selected）・入力の作成（built）・check・送信（submitted）・結果（outcome）に分けます。受理の中身（P6・U-R3a）は送信と別に数えます（`judge.accepted_content_by_check`）。

| 狙う操作・入力・結果 | デッキ・方策・規約集合 | 既存の到達の根拠 | 実行のときに見る値 | 届かなかったときに言えること・言えないこと |
|---|---|---|---|---|
| 突風・パソコン通信・エネルギー回収・ポケモン交換おじさん・ポケモン育て屋さんの play_trainer | C1・3 方式・CURRENT | エンジンの側の決まった手順の対戦だけ | `funnel.play_trainer` の各段階、`scope_excluded`・`build_failed` の理由、withheld の数、カードごとの選択・受理（行の `chosen`） | この 27 局・この方式で選ばれなかった、とだけ言える。エンジンが対応していないとは言えない |
| そこから出る決定（相手のベンチを選ぶ・山札から選ぶなど）と段の形 | C1 | 同上 | `axes.decision_kind`・`coverage.stage_feature`・入力の種類 | 同上 |
| 育て屋さんによる 2 進化 | C1 | 同上（[preset-decks-v0.26.md](preset-decks-v0.26.md) 6 章） | play_trainer の受理と、そのあとの場（記録） | 前提（番の最初から場にいるたね + 手札の 2 進化）がそろわなければ届かない。少数局では起きないことがある |
| 準備の切り直しの補償の続行 | C2・S2A（seed 2025） | なし（既定では止まる） | 終わり方・`convention_applied` の有無と場面・補償の決定の入力 | 場面の外なら、seed 2025 は S2A の補償の場面ではなかった、と言える。S2A 全体の正しさは言えない |
| 続行のない局の一致 | C2 と 99 局 | 99 局の指紋 | `sequences.json` の操作の列の指紋の一致 | 一致しても、ほかの seed・デッキでの一致は言えない |
| 停止方針・判定 | C1・C2 | 99 局 | 判定の件数、`undetermined_by_category`、known_stop、停止の理由 | 0 件でも、その種類の問題がないとは言えない |

### 5.2 読み方の注意

- 届かなかったことを、エンジンが対応していないことの証明にしない。
- 54 局の勝率・完走率を、強さ・網羅性の証明にしない。勝敗・きぜつの数え方は未計測のまま。
- 第2版のデッキの結果は、第1版の結果と同じ指標で比べてもよいが、デッキの差による違いとして読む。

## 6. 実装の変更が要る箇所（今回は実装しない）

推奨の C1・C2 は、今の道具（`c303da6`）のまま実行できます。次は、追加案のために要るものです。

| 箇所 | 中身 | 要る対象 |
|---|---|---|
| `batch.py`（計画・照合） | 固定デッキ以外のデッキリストを、出典（ファイル・名前）と内容の sha256 で計画に書き、照合する（V3-2 の `DECK_SOURCE` と同じ考え方） | マチスの秘策・スタジアム・新しい検証用のデッキ |
| `batch.py`（`MODES`） | profile boundary の方式（unverified を範囲に入れる）。deep の範囲・方策の順位は変えない | P6・U-R3a・unverified の選択・正常な拒否 |
| `batch.py`（CLI） | `game_reserve_seconds` を計画で指定できるようにする（任意） | 計画を 3 つ以上に分けるとき |
| 証跡の側の読み取りのスクリプト | `convention_applied` の件数・場面と、計画をまたいだ操作の列の比べ（最初に違う位置） | 規約集合の比べ |
| 集計（任意） | 勝敗・きぜつの数え方 | 成果の読み方 |

## 7. 追加案（推奨の計画の外。予算を超える・実装が要る）

| 案 | 中身 | 局・予算 | 前提 |
|---|---|---|---|
| 追加案 1: PO の一致 | 第1版の組・`CS-KYUURA-PLAY-PO@1`・C2 と同じ seed・方式 | 9〜27 局・予算 + 240 秒 | 実装は不要。10 分を超える |
| 追加案 2: マチスの秘策 | `L67`（`tools/existing_effect_games.py:1254`。ディグダ・エビワラー・ケーシィ・ユンゲラー・マチスの秘策 4・トレーナー 12・闘 15・超 14）の同型か、既存の組み合わせ（`PAIRINGS_V0_67`）。deep で、うらで出す・おもてにする・うらのワザ。boundary で P6 | 2 方式 × 数 seed | デッキリストと boundary の実装 |
| 追加案 3: スタジアム | `LUCKY_DECK`（`tests/test_legal_actions_u7_5d.py:398-406`。ほのおのデッキの炎 4 枚をラッキースタジアム 4 枚に）か、ニンジャジムのデッキ（`tests/test_ninja_gym_oracle_v0_146.py:56`）。`use_stadium` は may_stop_later なので deep で届く見込み | 数 seed × 3 方式 | デッキリストの実装 |
| 追加案 4: U-R3a | マチスの秘策と、特殊能力を持つたね・2 進化（例: フシギバナの系統）を入れた新しい検証用のデッキ（候補だけ。今は作らない） | — | 新しいデッキの採用・デッキリスト・boundary |
| 追加案 5: 固定の選び手 | 自然な方策では届きにくい P6・U-R3a・`use_stadium` を、new_game からの固定の選び手の合法な列で確かめる（V3-2 と同じ枠。自然な方策の実行とは別に数える） | 数局 | 実装が要る |

## 8. 採用の判断が要ること

1. C1・C2 の 2 計画（合計 54 局・上限 10 分・1 GiB）で実行してよいか。
   - C1 の予算 360 秒・C2 の 240 秒の分け方も含む。
   - 次の局を始める条件（150 秒）のために、実際に使える時間は合計 300 秒。
2. C2 の seed に、結果を見て選んだ 2025 を入れてよいか（ほかの 8 個は 99 局の計画の先頭）。
3. S2A（開発用の部分的な集合）を検証の対象にしてよいか。PO は追加案 1 にしたが、採るか。
4. マチスの秘策・スタジアム・boundary のために、バッチのデッキリストと boundary の方式を実装するか（6 章。別の作業）。
5. 新しい検証用のデッキ（追加案 4）を作るか。作るなら、出典と内容の確認値を記録する作業として別にする。

## 9. 実行するときの手順（案。確定した計画は、実行のときの `plan.json` と `plan.sha256`）

機械で読める下書きは [verification-ai-batch-plan3.json](verification-ai-batch-plan3.json) です。`status` が `draft` のあいだは、実行できる確定の計画ではありません。

1. 基点のコミット（実行のときの最新）と識別（版 0.179.0・`behavior_digest`・道具の識別）を記録する。
2. 実行の前の記録を保存する（事前の計画・デッキの確認値と合法性の検査・規約集合の識別）。
3. 計画を作る。
   - C1: `python -m tools.verification_ai.batch plan --batch vai-batch-c1 --seeds 3001 … 3009 --modes uniform-stage rules-v2 mixed --deck0 hitmonchan-dewgong-v2 --deck1 venusaur-parasect-v2 --max-games 27 --budget-seconds 360 --evidence-max-mb 640 --undetermined-evidence-missing continue`
   - C2: `… --batch vai-batch-c2 --seeds 2025 2001 … 2008 --conventions CS-KYUURA-PLAY-S2A@1 --max-games 27 --budget-seconds 240 --evidence-max-mb 384 …`
4. 実行する（単一のプロセス・逐次）。停止方針で止まったら、そこで報告する。
5. 集計し、`convention_applied` と操作の列の指紋を、99 局の保存済みの局と比べる。
6. 証跡を `verifier/`（完全な記録・trace・判定）と `public/`（非機密の集計）に置き、マニフェストを更新する。

## 10. 実行の結果（C1・C2。2026-11-11）

利用者が 3 章の C1・C2 を採用し、そのまま実行した（PO・新しいデッキ・boundary・seed の探索は足していない。予算は延長していない）。
9 章の下書き（[verification-ai-batch-plan3.json](verification-ai-batch-plan3.json)）は確定の計画ではない。確定の計画は、証跡の `plan.json` と `plan.sha256`。

### 10.1 基点・確定の計画・実行の前の確認

- 実行コミット: `claude/vai-batch-plan3` の `9385cc3`（エンジン・道具とも。P6 の判定の接続 `c303da6` を含む。`origin/main` `7b3d53c` には未取り込み）。リポジトリのコードは変えていない
- 識別: 版 0.179.0・`behavior_digest` `67c4c15b…7fca`（99 局と同じ）・道具 TOOL_VERSION 3・道具の識別 `d40e2b8c…b3cf`・計画の形式 3・完了の形式 3。実行の後の識別も同じ（`identity_after.json`）
- デッキ（`preflight.json`）: 4 デッキとも 60 枚で、`deck_problems` は空。内容の確認値（`canonical(cards)` の sha256。batch の `deck_check` と同じ方法）:

| デッキ | 確認値 |
|---|---|
| `hitmonchan-dewgong` | `cf9746e3b7e1f11d…` |
| `venusaur-parasect` | `2e3c9044590c7ef0…` |
| `hitmonchan-dewgong-v2` | `66e569289363117e…` |
| `venusaur-parasect-v2` | `a0831f9d5ac0c094…` |

  第2版だけのカード: PMCG1-007 モンジャラ・PMCG1-072 突風・PMCG1-076 エネルギー回収・PMCG1-090 パソコン通信・PMCG1-093 ポケモン交換おじさん・PMCG1-094 ポケモン育て屋さん（第1版だけは PMCG1-079）
- 規約集合: C1 `CS-KYUURA-CURRENT@1`（`sha256:9a9b95c6…3cee`）、C2 `CS-KYUURA-PLAY-S2A@1`（`sha256:b317a3f0…10c4`）
- 確定の計画:

| 計画 | 局 | 上限 | `plan.sha256` |
|---|---|---|---|
| `vai-batch-c1` | 27 | 360 秒・640 MiB | `e8956a7f0485d57e8f7c025f226700cb58533ecaf000920332c65b83908cbd20` |
| `vai-batch-c2` | 27 | 240 秒・384 MiB | `d675ef4ee4a479ab4098a7e2f4125839376b9dac3bf43fe27349fb8e50e5642b` |

  各局の `game_id`（`g001-uniform-stage-s3001` など）は一意。ゲーム・方策・ホストの seed は同じ値（runner が主体ごとに分ける）。mixed は rules-v2・ε 0.25。単局の上限は既定（操作 2000・受理 1000・番 200・120 秒）。次の局を始める予備は 150 秒。停止方針は 3.4 節のとおり（既定）。計画の各局のデッキの確認値・規約集合・実装識別が `preflight.json` と同じことを確かめた

### 10.2 完了・停止・時間・資源

| | C1 | C2 |
|---|---|---|
| 完了／計画 | 27／27（未完了・未着手 0。attempt は各局 1） | 27／27（同じ） |
| 終わり方 | game_over 27 | game_over 26・limit_accepted 1（seed 2004・rules-v2。99 局の同じ局も limit_accepted） |
| バッチの停止（停止方針による停止）・承認・再開 | なし（1 セッション） | なし（1 セッション） |
| replay_run | 27 局とも succeeded（期待どおり） | 27 局とも succeeded（期待どおり） |
| 累積の時間 | 81.234 秒（局の合計 57.1 秒・中央 1.93 秒・最大 6.13 秒） | 91.826 秒（局の合計 64.2 秒・中央 1.63 秒・最大 19.0 秒） |
| 自分のプロセスの最大の作業セット | 192,962,560 バイト | 348,213,248 バイト |
| ゲームの証跡 | 144,615,723 バイト（約 138 MiB） | 159,768,826 バイト（約 152 MiB） |

合計 173.1 秒（予算 600 秒）・約 290 MiB（予算 1 GiB）。

この文書の「停止 0」は**バッチの停止 0**（停止方針でバッチを止めた回数）を指す。送信の拒否（C1 の 15。10.3 節）と、受理の上限による局の終わり（C2 の limit_accepted 1）は、バッチの停止とは別に数える。

方策ごと（各 9 局。上限に届いた局は C2 の rules-v2 の 1 局だけ）:

| | C1 受理・番 | C1 方策の抑制 | C2 受理・番 | C2 方策の抑制 |
|---|---|---|---|---|
| uniform-stage | 1109・360 | 0 | 1171・370 | 0 |
| rules-v2 | 1911・372 | 124 | 2053・248 | 226 |
| mixed | 1643・386 | 14 | 1351・320 | 8 |

### 10.3 判定

- C1: 送信 4678 のうち、受理 4663 は expected。拒否 15 は undetermined（分類 `evidence_missing_stop`。理由 `stop_condition_not_evidenced:UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`）で、停止方針どおり記録して続けた。終わり方 27 は expected。suspect 0・known_stop 0・受理の中身（U-R3a・P6）0・異常 0
  - 15 件はどれも、エネルギー回収の受理のあとの決定 `retrieve_energy`（段の枚数 最小 0・最大 1〜2）で 0 枚を選んだ送信。check は valid、送信は `unresolved_ruling` の拒否。裁定の記録（[rules-2000-02-14.md](rules-2000-02-14.md) ER9。「最大2枚」が 0 枚を含むかは決まらない）どおりの停止で、決定は待ったまま。replay_run は 27 局とも成功で、拒否による状態の変化は検出されていない
  - そのあと同じ入力の再送は 5 回抑えられ（`retry_same_input`）、15 件とも 1〜2 枚を選んで受理された
  - undetermined になったのは、このコードの代表の条件の根拠（`KNOWN_STOP_EVIDENCE`）が judge にないため。不具合候補とは扱わない。根拠を足すかは別の作業
  - 11 章で根拠を確かめ、判定の規則 6 で条件つきの根拠を登録した（保存済みの trace への当て直しでは、この 15 件が known_stop）。ここの件数は規則 5 での判定のまま残す
- C2: 受理 4575 は expected。拒否 0。終わり方 27 は expected（limit_accepted は道具の上限）。undetermined・suspect・known_stop・異常は 0

### 10.4 到達（C1）

候補の種類（提示）は 99 局と同じ 14 種類（API の 20 種類のうち）。提示されていない 6 種類（`use_stadium`・`reveal_face_down`・`remove_disguise`・`discard_from_play`・`start_sudden_death`・`check_face_up_deck`）は未到達のまま。
選んだ候補の処理可能性は supported・may_stop_later だけ、状況は actor_to_act だけ、check の invalid・断り・入力の生成の失敗による停止は 0。

新しく届いたもの:

- 送信の結果の rejected（15。上の 10.3 節）
- 決定の種類が 3 → 8（`discard_from_hand` 129・`search_deck` 102・`retrieve_energy` 71・`return_to_deck` 24・`select_evolution_card` 6 が新しい。ほか `select_pokemon` 183・`take_prize` 86・`promote_active` 80）

第2版だけのカードの到達（`reach_c1_v2cards.json`。「選べるものにあった」は選んだ候補の入力の段にあった試み。デッキにあることとは別に数える）:

| カード | 選べるものにあった局 | 選ばれた局 | 受理された局 | 使用の受理（候補の種類） | 直後の決定（件数） |
|---|---|---|---|---|---|
| PMCG1-007 モンジャラ | 24 | 22 | 22 | play_basic 27（ほかに場のポケモンとして attach_energy 49・use_attack 43 など） | — |
| PMCG1-072 突風 | 27 | 24 | 24 | play_trainer 57 | select_pokemon 57（すべて受理） |
| PMCG1-076 エネルギー回収 | 27 | 24 | 24 | play_trainer 51 | discard_from_hand 51・retrieve_energy 71（受理 102・拒否 15・再送の抑制 5） |
| PMCG1-090 パソコン通信 | 26 | 26 | 26 | play_trainer 78 | discard_from_hand 78・search_deck 78（すべて受理） |
| PMCG1-093 ポケモン交換おじさん | 26 | 22 | 22 | play_trainer 24 | return_to_deck 24・search_deck 24（すべて受理） |
| PMCG1-094 ポケモン育て屋さん | 19 | 18 | 18 | play_trainer 6 | select_evolution_card 6・select_pokemon 6（すべて受理） |

- 「選ばれた局」「受理された局」は、使用のほかに、決定の答えとして選ばれた場合（パソコン通信でトラッシュする手札など）も数える。使用の受理の件数は右の列
- 「直後の決定」は、受理された play_trainer の直後に続いた answer_decision を、trace の並びで対応づけたもの（エンジンが「このトレーナーの決定」と示した値ではない）
- ポケモン育て屋さんの使用の受理は 6 件と少ない
- 範囲外: 処理可能性 unresolved_ruling で除いた候補 290、入力を作れない（`total_units_unreachable`）1062。方策の抑制 138（同じ行動の反復の抑制）

### 10.5 S2A の規約の適用と、99 局との比較（C2）

比較は `compare_c2_b2.py`（証跡に保存。保存したファイルを読むだけで、方策・行動生成を動かさない）。`convention_applied` はログにだけあり、完全な記録・trace には直接書かれないので、
保存した完全な記録を `replay_run.replay` の observer で再実行して読んだ（各局の検証の replay_run と同じ入口。54 局とも成功）。

比べた形式・道具の違い: 計画の形式 3 と 2、完了の形式 3 と 2、道具の版 3 と 2（識別 `d40e2b8c…` と `420244af…`）、停止方針の `on_undetermined` に `accepted_content_unrecorded` があるか、バッチの上限。
局の設定（config の全項目）の違いは、27 組とも `conventions` と `run_id` だけ。方策（名前・版・分布・seed・ε・閾値）とデッキは 27 組とも同じ。

| 群 | 組 | 規約の適用 | 行動の列（action-meaning/v2） | 契約の値の列 | 完全な記録の操作の行 | 判定 |
|---|---|---|---|---|---|---|
| 比較条件（seed 2001〜2008） | 24 | 0 | 24 組とも同じ（長さも同じ） | 24 組とも同じ | 24 組とも同じ | 一致 24 |
| 回帰条件（seed 2025） | 3 | 各 1 | 位置 0 から違う（99 局は 0 行） | 位置 0 から違う | 違う（99 局は 0 行） | 適用後の差 3 |

- 比較条件 24 組の完全な記録の違いは、記録・API の識別の違いだけ: 見出しの `convention_set`・`initial.conventions`・`game_id`・開始の確認値、各行の確認値のうち `state` だけ（`rng`・`log_length`・`status` などは同じ）、`operation_id` の局の識別の部分だけ（残りは同じ）。
  `state` の確認値は規約集合の識別を含む状態の指紋なので、行動の意味の違いとは扱わない。終わり方も 24 組とも同じ（game_over 23・limit_accepted 1）
- 回帰条件（seed 2025・3 方式）:
  - 99 局（CURRENT）: 3 局とも開始で `halted_known`（`UNRESOLVED_MULLIGAN_COMPENSATION`。操作 0。judge は termination undetermined・`evidence_missing_stop`）
  - C2（S2A）: 3 局とも開始で `PC-SETUP-MULLIGAN-COUNT`@1 を 1 回適用（場面 `UNRESOLVED_MULLIGAN_COMPENSATION#initial-setup`・コード `UNRESOLVED_MULLIGAN_COMPENSATION`・記録の行 0 の前＝最初の試みの前。公開の値 player 0・rounds_both 1・rounds_single 1）。そのあと game_over まで進んだ（受理 137・158・171）。適用はこの 1 回だけで、ほかの場面（`#sudden-death-segment` など）の適用はない
  - 最初の違いは適用の位置（試みの 0 行目の前）で、適用より前の違いはない。適用後の差は、規約の適用と矛盾しない差だが、規約だけの因果的な効果とは断定しない（比べる相手は開始で止まっていて、適用のない進み方は観測できない）
  - 回帰条件は結果を見て選んだ seed なので、比較条件の 24 組と分けて数えた
- 不具合候補・判断不能は 0

### 10.6 失敗・修正・再実行・未確認

- 比較・到達の小さな処理のテスト（`test_compare_scripts.py`。人工の例と、保存済みの 99 局の記録 3 つ。13 件）: 1 回目に 1 件の失敗（`reach_cards.py` の数えの関数に、数の 1 を鍵として渡していた）。直して 2 回目 13 件 OK。そのあと比較に「確認値の違う項目」と「局の識別を除いた operation_id」を足して再実行（3 回目 13 件 OK。判定の件数は 1 回目と同じ）。1 回目の出力は `compare_c2_b2_run1.json` として残した
- マニフェストの 1 回目: 出力を証跡の中に書いたため、書き込み中の出力自体がマニフェストに入った。また public の要約に seed と局の識別が入っていた（public の約束に反する）。1 回目で足した 697 項目だけを除いて、前の `sha256.json`（`2a62759a…7e7d`）にバイト単位で戻ったことをハッシュで確かめ、public の要約を群ごとの件数だけに直して、出力を証跡の外へ書いて 2 回目を実行した
- 対戦の再実行はない（各局 attempt-001 だけ）
- 未確認: 決定の答えの入力に、見えてはいけない情報が含まれないか（山札を探す決定 `search_deck` の選べるもの）は、この単位では調べていない（11.4 節で、保存した範囲を調べた）。判定は受理・拒否・終わり方の契約までで、カードの効果の結果の正しさ（状態の中身）は調べていない。勝敗は数えていない

### 10.7 証跡

保存先 `C:/dev/kyuura-engine-verification-vai/`:

- `verifier/runs/vai-batch-c1/`・`verifier/runs/vai-batch-c2/`: 計画・台帳・各局（完全な記録・trace・本人向けの記録・判定・replay_run・指紋）・集計
- `verifier/runs/vai-batch-c/`: 実行の前の確認（`preflight.py`・`preflight.json`）・計画と実行と集計の出力と終了コード（`sessions/` ほか）・比較（`compare_c2_b2.py`・`compare_c2_b2.json`）・到達（`reach_cards.py`・`reach_c1_v2cards.json`）・テスト・`identity_after.json`・`commands.txt`
- `public/runs/vai-batch-c1/`・`public/runs/vai-batch-c2/`・`public/runs/vai-batch-c/`: seed・局の識別・デッキの並び・選択の中身を含まない集計
- マニフェスト: 既存の 2359 項目を照らして不一致・欠け 0、696 項目を足して 3055 項目。`sha256.json` = `53a604a6750219601e7de742315654c02ecd73899451fd47dc35730f0a4bfe60`

### 10.8 次に広げる前の判断材料

1. 第2版のトレーナーの決定（5 種類）は届いた。ポケモン育て屋さんの使用の受理は 6 件と少ない。
2. `UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE` の拒否は、裁定の記録どおりの停止だが、judge には代表の条件の根拠がない（undetermined）。judge に根拠を足すかを判断する。→ 11.2 節（規則 6 で条件つきで登録）
3. API は、この決定で 0 枚を選べる段（最小 0）を示し、check も valid を返す。そのため、方策は 0 枚を選んで拒否されうる。候補の保証の文は受理を保証していないので、契約には反しない。この組み合わせを残すか、文書で明示するかを判断する。→ 11.3 節・11.7 節（変えずに案を保留）
4. S2A の比較条件 24 組は、99 局と行動の列が一致した。回帰条件では、補償の規約の 1 回の適用のあと、対戦が最後まで進んだ。延長戦の区間の場面（`#sudden-death-segment`）と、ほかの続行規約の場面には届いていない。
5. P6・U-R3a・スタジアム・未提示の 6 種類・unverified の選択・check の invalid・断りは未到達のまま。届くには、6 章のデッキリストと boundary の方式の実装が要る（この単位の対象外）。

## 11. C1・C2 の結果の確認（3 点。2026-11-11）

10.8 節の 2・3 と、10.6 節の未確認（`search_deck` などの情報の公開）を確かめた。**新しい対戦はしていない**（seed の探索・双子の実行もない）。保存済みの 54 局と 99 局の証跡、コード、文書を読んだ。
エンジン本体・方策・行動生成・GUI・renderer・カードデータ・固定デッキ・規約集合・裁定・識別方式・版（0.179.0）は変えていない。変えたのは judge の限定の修正とその関連テストだけ（11.2 節）。

- 基点: `claude/vai-batch-plan3` の `73e3885`（`origin/main` `7b3d53c` には未取り込み。取り込みを仮定しない）
- 作業開始時の計画（読み取りの対象・確認の方法・変更を許可する範囲）は、確認の結果を見る前に証跡の `00_plan.md` に保存した
- 確認用のスクリプトは証跡に置いた（`tools/verification_ai/` には入れていない）。ゲームを動かさず、保存済みの JSON・JSONL を読んだ。当て直し（11.2 節）だけは judge を import する（エンジンの診断のコード表を読むため。対戦は作らない）

### 11.1 証跡で確認できる範囲

| 記録 | 中身 | 使える範囲 |
|---|---|---|
| `actors/<0\|1>.jsonl` | その主体が**行動する番に**取得した応答だけ（`position` の view＝その時点の本人の観測。`attempt` の candidates・inputs・check・submit の応答） | 本人に返した情報。相手が行動しないあいだの観測・公開の更新は**入っていない**。全配信の証拠には使わない |
| `actors/host.jsonl` | ホストの要求（ジャンケンの 2 件） | — |
| `trace.jsonl` | 検証者の記録（候補・段・選んだ入力・応答・検証者用の診断） | 検証者だけの情報 |
| `full_record.json` | 完全な記録。受理の行には確認値（状態・乱数・ログの長さ・決定・区分）。**拒否の行は確認値を持たない** | 検証者だけの情報 |
| `verification.json` | replay_run の結果。再実行の中で、拒否の行ごとに状態が変わらないこと（`state_changed_by_rejection`）を照らしている | 拒否で状態・乱数・ログ・決定が変わらないことの、再実行による確認 |
| `result.json` の `anomalies` | 実行中の照らしの結果。拒否のあとに 4 つの閲覧者の更新を取り出して、あれば `update_after_rejection`。拒否で状態が変わったら `state_changed_on_rejection` | 更新の**中身は保存していない**。なかったことは、異常の記録がないことでだけ示される |

保存していないもの（この単位では「未確認」とし、記録にあるかのように補わない）: 公開の更新（相手・観戦者・ホストへの update）の中身、観戦者の観測、ログ（visible_log）、相手が行動しないあいだの相手の観測、拒否の直後の状態の確認値。

### 11.2 エネルギー回収の 0 枚の拒否 15 件（`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`。ER9）

**照合（コードと文書）**

| 対象 | 内容 |
|---|---|
| 裁定 | [rules-2000-02-14.md](rules-2000-02-14.md) の ER9・[energy-retrieval-v0.23.md](energy-retrieval-v0.23.md): 選べる基本エネルギーカードがあるのに 0 枚を選べるか（「最大2枚」が 0 枚を含むか）は決まらない。決定は待ったまま |
| エンジン | `effects.py` の `DiscardFromHandThenRetrieveEnergy`: 段階 2 の決定 `RETRIEVE_ENERGY` を `min_choices=0`・`max_choices=min(2, 選べるものの数)` で出し（選べるものが 0 なら不具合として RuntimeError。使う前の確かめ ER10 で除く）、`resume` で答えが空なら `UnsupportedError(ZERO_CHOICE)`。コマンドは状態の複製の上で処理するので、決定は待ったまま |
| 停止の分類表 | `stop-policy-classification.json`: `research_stop_code`・機構 `answer_rejection`・裁定 ER9・族 PF-UP-TO-ZERO・場所 `effects.py:6664`（今のコードと同じ行） |
| 診断のコード表 | `diagnostic_catalog.json`: 分類 `unresolved_ruling`・`raised_as` unsupported |
| 既存のテスト | `tests/test_energy_retrieval_v0_23.py` の `test_zero_cards_is_unresolved_and_keeps_the_decision`（止める・決定は待ったまま・段階 1 のトラッシュは取り消さない・1 枚以上で選び直せる） |
| judge の既存の登録 | 規則 3: `KNOWN_STOP_EVIDENCE`（DU1 だけ）に登録があり、**場面の側（fixture）が同じコードを宣言した**ときだけ known_stop。逐次バッチの判定（`batch.judge_trace`）は宣言を渡さないので、どの停止も known_stop にならない |

4 つは互いに一致する。

**15 件ごとの照合**（`audit_er9.py`・`audit_er9.json`。全件。15 件 × 31 項目がすべて成り立った）

- 要求: 候補は `answer_decision`、段は 1 つで `decision_kind` `retrieve_energy`・最小 0（`decline` true）・選べるもの 1〜12 枚（最大 1〜2）。選んだものは 0。check は valid。候補の理由に `continuation_not_evaluated`
- 診断と分類: 送信は rejected。検証者の診断・公開の結果の `diagnostic_id`・エンジンのコードがそろい、分類 `unresolved_ruling` はコード表と同じ。取り直しは不要（`refetch_required` false）
- 決定: 拒否の前の受理の行の確認値で、本人の `retrieve_energy` の決定が待っていた。完全な記録の拒否の行は、その決定の番号に答える `resolve_decision`（choices 空）。拒否の結果は本人の決定待ち（`awaiting_decision`・next は本人の answer_decision）
- 状態・乱数・ログ・決定が変わらない: replay_run が 15 件の行を含めて成功（再実行の中の `state_changed_by_rejection` の照らし）。実行中の照らしでも `state_changed_on_rejection` の異常はない。拒否の行そのものの確認値は保存していない（未保存）
- 他者への新しい更新: 実行中、拒否のあとに 4 つの閲覧者の更新を取り出す照らしで、`update_after_rejection` の異常はない（更新の中身は未保存）。コードでも、拒否では公開の更新を作らない（`client_api.ClientHub._on_result`）
- 選び直し: 15 件とも、完全な記録の次の行が同じ決定への答えで受理された（あいだにほかの操作はない。13 件は 1 枚・2 件は 2 枚。同じ主体。乱数の確認値は拒否の前と選び直しの受理のあとで同じ）

**再送の抑制 5 件の仕組み**: どれも、runner の局面ごとの集合 `tried`（check が invalid・送信が拒否・断りになった入力の署名）に同じ署名（同じ候補・同じ意味の入力＝0 枚）があったため送らなかったもの（`build` `ok_already_tried`）。直前の同じ入力は 15 件のどれか（ER9 の拒否）。
方策の戦略の反復の抑制（`policy_suppressed`・`policy.review`）ではない（5 件とも `policy_review` なし。check・送信なし）。そのあとの候補・枚数の選び直しは、方策の通常の選び（uniform の枚数の選び。rules-v2 も決定の答えは `rule2:fallback:no_priority`）で、0 枚を除いてはいない。
0 枚の選択を AI 側で違法扱いして除外する処理はない（変えていない）。

**根拠の登録（判定の規則 6）**: 裁定・エンジン・分類表・既存のテスト・15 件の記録がそろったので、**今回の条件に限って**登録した（コミット `05cd8c4`）。

- `judge.KNOWN_STOP_EVIDENCE` に ER9 の条件と根拠を登録し、`RECORDED_STOP_CONDITIONS`（ER9 だけ）と `recorded_stop_evidence` を加えた。`recorded_stop_evidence` は、記録した送信の **API の値だけで**次をすべて満たすときだけ、コードを根拠として返す:
  候補が `answer_decision`・段が 1 つで `decision_kind` `retrieve_energy`・最小 0・最大 1 以上・選べるもの 1 つ以上・選んだもの 0・拒否で検証者の診断と公開の結果のコードがそろう・拒否のあとも本人の決定待ち（`awaiting_decision`、next が本人の answer_decision だけ）・取り直し不要
- `batch.judge_trace` がそれを `judge_normal` の `evidence` に渡す。コードが同じでも条件を満たさない送信と、ほかのコードは規則 5 と同じ（undetermined のまま）。単局の runner の判定（evidence を渡さない）・方策・行動生成・乱数の消費は変えていない
- 版: `JUDGE_RULES_VERSION` 5 → 6、`TOOL_VERSION` 3 → 4。道具の識別 `d40e2b8c1df043048cbccc62d7773f3bbe51b02ee596e94d537e2080df23b3cf`（73e3885。C1・C2 の実行と同じ）→ `60a16e49c6aefabfdf703b6b513b2b36c1cac7cbcbf9355abf72f9faa9191850`（05cd8c4）
- 影響: 識別が変わるので、既存の計画（C1・C2・99 局）を新しい道具で実行・再開することはできない（再開しない）。今後の逐次バッチでは、この条件の ER9 の拒否は known_stop（停止方針の `on_known_stop`。今の計画の既定は continue）
- 同じ形のほかのコード（11.3 節）は、根拠を個別に確かめていないので登録していない

**当て直し**（`rejudge.py`。保存済みの trace に当て、別の出力 `rejudge_before.json`・`rejudge_after.json` に書いた。元の `judge.json`・集計・完了マーカーは変えていない。旧バッチを再開・再確定したとは扱わない）

| | 局 | 送信の行 | 規則 5（変更の前）で当て直し | 規則 6（変更の後）で当て直し |
|---|---|---|---|---|
| C1 | 27 | 4678 | 27 局とも保存の `judge.json` と同じ | 15 行が undetermined → known_stop（11 局）。ほかの行・終わり方・受理の中身・ER9 以外の undetermined は同じ |
| C2 | 27 | 4575 | 27 局とも同じ | 行の変化 0（規則の版の値だけが違う） |
| 99 局（b2） | 99 | 15654 | 送信の行・終わり方・undetermined・known_stop は同じ。受理の中身の欄の形だけが違う（99 局は道具の版 2 で作り、種類ごとの欄がない） | 行の変化 0。seed 2025 の 3 局の準備の停止（`UNRESOLVED_MULLIGAN_COMPENSATION`。受理のあとの停止）は undetermined のまま |

suspect・ほかの undetermined の分類は、どのバッチでも変わらない。保存した 10 章の判定（C1 の undetermined 15・known_stop 0）は、規則 5 での判定としてそのまま残す。

### 11.3 最小 0 の段・check・実行時の拒否の契約

| 段階 | 内容 |
|---|---|
| 段の制約 | 決定の候補の段は、決定の `min_choices`・`max_choices` をそのまま `count` に写し、`decline` は `min_choices == 0`（`legal_actions.py` の決定の候補）。ER9 の決定は最小 0 なので、0 枚は**構造上許される** |
| 選べるものの印 | 選ぶと止まる選べるものは、決定の `unresolved_choices` で選べるものごとに印をつける（実行できない区分）。**空の答えに印をつける仕組みはない** |
| check | 入力の検査（`_input_problem`）は、選べるものの番号・重なり・枚数の範囲・選べるものの実行できる区分だけを見る。空の答えは範囲内で、選んだ選べるものがないので valid |
| 候補の保証 | `acceptance`「保証しない（最終の判定は apply_command）」、`after_acceptance`「評価していない（効果の続きで、決定待ち・停止・未裁定や未対応による拒否がありうる）」、`preconditions` は check と同じ公開の制約。処理可能性 `may_stop_later`・理由 `continuation_not_evaluated` |
| 実行時 | エンジンの `resume` が空の答えを `UnsupportedError` で止め、結果は rejected（`unresolved_ruling`）。状態は変わらず、決定は待ったまま |
| 拒否のあと | 同じ取っ手で選び直せる（15 件とも、1 枚以上の答えが次の行で受理） |

したがって、check の valid のあとの拒否は、候補の保証（受理を保証しない）の範囲で、契約には反しない。ただし「どの答えが止まるか」は空の答えについては API に出ない。
この単位では API の最小値・check の可否・エンジンの拒否条件を変えていない。変える案は 11.7 節に保留として書いた。

**同じ形の箇所**（静的な調べ。`static_zero_choice.md`。73e3885 のコードを読んだだけで実行していない。大部分は読み取り専用の補助のエージェントの調べで、主が読み直して確かめたのは ER9・みらいよち・決定の段と入力の検査）:

- ER9 と同じ形（決定の答えで、最小 0、空の答えを `resume` で止め、決定は待ったまま、印なし、check(空) は valid）: 超エネルギー回収（SR2。ER9 と同じ関数を継承しコードだけ上書き）・夜の廃品回収・ロケット団のワナ・`UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE`（3 か所）・`UNRESOLVED_DISCARD_ANY_NUMBER_ZERO`（6 か所。挑戦状は決めるのが相手のことがある）・`UNRESOLVED_DISCARD_UP_TO_ZERO`・`UNRESOLVED_ATTACH_FROM_DISCARD_ZERO`（5 か所）・`UNRESOLVED_RECOVER_ZERO_ENERGY`・`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`（ギガスパークなど 2 か所）・`UNRESOLVED_POWER_ZERO_CARDS`（4 か所）。山札のカードを選ぶ決定の一部は、候補を伏せる場合があり、check(空) が valid かは未確認
- 形が違う:
  - **みらいよち**（コードは `UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`）: 0 は「見る枚数」の選べるものの**値**。最小は 1、値 0 に印がなく、空でない答え（値 0）が check を通って拒否される。同じコードが別の形の箇所で使われる例
  - ポケモン図鑑・善行・`UNRESOLVED_HEAL_UP_TO_ZERO`: 0 にあたる選べるものに印があり、check は `CANDIDATE_NOT_EXECUTABLE`（契約と整合）
  - ベンチガード（kernel）: 逆の形（空の答えは受理し、空でない選べるものに印）。`UNRESOLVED_CHARITY_BELOW_ZERO`: 0 枚を選ぶ問いではない（ダメージの計算）
  - 使う・宣言するときの、対象がないときの拒否（決定の前）。ファイヤーブースト（最大を選べるものの数で切らない）。ワザの要素の先読みは 0 の答えを試さない

### 11.4 `search_deck` などの情報の公開

対象は C1 の `search_deck`・`return_to_deck`・`discard_from_hand`・`retrieve_energy`。**全件**（C1 の 27 局のすべての保存済みの観測 4636・試み）を、保存済みの記録だけで調べた（`audit_disclosure.py`・`audit_candidates.py`・`audit_search_order.py`）。
**情報の漏れらしいものは見つからなかった**（issues 0）。ただし相手・観戦者への更新とログは保存していないので、その部分はコードの読み取りだけ（未確認と区別する）。

**件数の定義と生成元**: `search_deck` の 102 は、`result.json` の `coverage.decision_kind`（入力を作った試みの段の `decision_kind` を数える）の合計。trace で段が `search_deck` の試みも 102、決定（局面）も 102 で、拒否・再送の抑制はない。生成元は、その時点の本人の観測の `trainer_in_use` で分けた:

| 決定 | 決定 | 生成元のカード | 回答者に示した選べるもの | 範囲の照合（全件） |
|---|---|---|---|---|
| search_deck | 102 | パソコン通信 78・ポケモン交換おじさん 24 | 山札のカード（uid と card_id） | パソコン通信: 選べるものの数＝本人の山札の枚数、手札・トラッシュのカードを含まない、1 枚ちょうど（78／78）。交換おじさん: ポケモンのカードだけ、山札の枚数以下、1 枚ちょうど（24／24。山札の中身そのものは記録にないので、選べるものが山札のポケモンの**すべて**かは未確認） |
| return_to_deck | 24 | ポケモン交換おじさん 24 | 本人の手札のポケモンのカード | 手札のポケモンのカードの数と一致（24／24） |
| discard_from_hand | 129 | パソコン通信 78・エネルギー回収 51 | 本人の手札（使っているカードを除く）すべて | 手札と一致（129／129） |
| retrieve_energy | 51（試み 71） | エネルギー回収 51 | 本人のトラッシュの基本エネルギーカード | トラッシュの基本エネルギーカードから、段階 1 でトラッシュしたカードを除いたものと一致（51／51。ER6・ER11） |

時点ごとの確認:

| 時点 | 記録で確かめたこと（全件） | 記録にない・コードだけ |
|---|---|---|
| 検索を起こす操作の候補・check | パソコン通信・交換おじさん・エネルギー回収の使用の選べるものの値の組は 5 通りだけ。使えない（`unresolved_ruling`）のは、パソコン通信が山札 0 枚（公開の枚数）の 3 件、エネルギー回収がトラッシュに基本エネルギーカードがない（公開のトラッシュ。ER10）29 件。山札の中身で変わる値は出ていない（選ばなかった候補の段は取得していないので、保存された段の範囲だけ） | — |
| 受理と決定の生成 | 本人の観測の決定の種類・決める人・選べるもの（値・card_id）・`option_count` が、段の選べるものと一致（326／326 の試み）。検索を始める前の本人の観測の山札は枚数だけ（4636 の観測すべて） | — |
| 回答者向けの view・candidates・inputs・check | 段の選べるもの・最小と最大は回答者のファイル（本人の要求の履歴）にだけある。相手のファイルに、もう一方の決定の段の試みはない（0）。`search_deck` の選べるものは 102／102 が uid の昇順で、山札の並びを示さない | 未選択のカードの card_id は、検索の決定のあいだ回答者に示される（山札を探す効果で見る権利がある。`DECK_REVEALING_KINDS`） |
| 相手・観戦者への応答と更新 | 相手のファイルの観測（相手が行動する番のもの）で、もう一方の手札は中身なし（4636／4636。見せた手札もない）、山札は枚数だけ、裏のサイドの中身なし、置いておくカードの中身なし。相手が決める人でない決定を見た観測は記録に 0 件（相手は決定のあいだ行動しない） | 決定のあいだの相手・観戦者の観測と更新は未保存。コード: 決める人でない人には決定の種類・決める人・（数を伏せない種類だけ）枚数と選べるものの数を見せ、選べるものは見せない。`search_deck`・`return_to_deck`・`discard_from_hand`・`select_evolution_card` は `HIDDEN_COUNT_KINDS` で、数も見せない（`observation._decision`）。`retrieve_energy` の数は公開のトラッシュで決まる |
| 回答後の公開・移動 | 検索で選んだカード（102 枚）の uid は、それが本人の手札にあるあいだの相手の観測（724）のどこにも出ていない | ログは未保存。コード: `search_deck`（パソコン通信）の `card` は本人だけ（文面に見せる指示がない。CS14）、`reveal_from_deck`（交換おじさんの段階 2）・`return_to_deck`（段階 1）は全員（文面「相手プレイヤーに見せてから」）、`discard_from_hand`・`retrieve_energy` は全員（トラッシュは公開。ER13） |
| シャッフルと終了後 | シャッフルのあとも、本人の観測の山札は枚数だけ（並びを示さない） | 終了後の観測は記録にない（未確認） |

選んだカードの公開は、カードの文面・採用の裁定・公開の規則（ログの見える範囲）と合っている（パソコン通信は本人だけ、交換おじさんは全員）。限界: 更新・ログ・観戦者の観測を保存していないこと、交換おじさんの選べるものが山札のポケモンのすべてかを記録から確かめられないこと、C1 の 2 デッキ・27 局の範囲だけであること。

### 11.5 失敗・修正・未確認

- テストの失敗・再実行はない（新しいテスト 7 件・版の表明を変えた 5 つと判定の関連のテストを、1 つずつ別プロセスで実行。どれも exit 0）。全体のテストは実行していない
- 公開の情報の調べの途中で、エネルギー回収の選べるものの範囲の比べを書き直した（最初の式は段階 1 でトラッシュしたカードを除く比べになっていなかった。実行の前に直し、実行は 1 回）
- 未確認: 公開の更新・観戦者の観測・ログの実物、拒否の直後の状態の確認値（replay_run・実行中の照らしの結果だけ）、交換おじさんの選べるものの完全さ、同じ形のほかのコードの実行時のふるまい（静的な調べだけ）、山札のカードを選ぶ決定で check(空) が valid か

### 11.6 証跡

保存先 `C:/dev/kyuura-engine-verification-vai/`:

- `verifier/runs/vai-batch-c-audit/`: 作業開始時の計画（`00_plan.md`）・確認のスクリプト（`audit_er9.py`・`rejudge.py`・`audit_disclosure.py`・`audit_candidates.py`・`audit_search_order.py`・`identity.py`・`build_public.py`）と出力・終了コード・静的な調べ（`static_zero_choice.md`）・当て直しの別の出力（`rejudge_before.json`・`rejudge_after.json`）・テストの出力・道具の識別（`identity_after_change.json`）・`commands.txt`
- `public/runs/vai-batch-c-audit/summary.json`: 件数だけ（seed・局の識別・選択の中身を含まない）
- 元の `vai-batch-c1`・`vai-batch-c2`・`vai-batch-b2` の判定・集計・完了マーカーは変えていない
- マニフェスト: 既存の 3055 項目を照らして不一致・欠け 0、37 項目を足して 3092 項目。`sha256.json` = `971e565aeff977ac351d3505afc1b5fbbcb905baa680d2e618633871a4d67856`（更新の出力は証跡の外に書いた）

### 11.7 デッキリスト・boundary の実装へ進む前の判断材料

1. ER9 は規則 6 で、条件を確かめたときだけ known_stop になる。同じ形のほかのコード（11.3 節）を同じ方法で登録するかは、それぞれの裁定の記録・テスト・観測した記録がそろってから判断する（コード名だけで広げない。みらいよちのように同じコードで形が違う箇所がある）
2. 空の答えが止まることは API に出ない。保留した案（変えていない）: (a) 決定の段に「空の答えは未裁定で止まる」ことを示す値を加える（API の契約の変更。`legal_actions`・クライアントの契約の文書・GUI に影響）、(b) 候補の保証の文に、最小 0 の段の空の答えが止まりうることを書く（文書だけ）、(c) 今のままで、検証の側の規則 6 のように記録で読む。みらいよちは空でない答えが check を通るので、(a) の値だけでは足りない（選べるものの印 `unresolved_choices` を使うかの判断が別に要る）
3. 情報の公開は、保存した範囲で漏れは見つからなかった。更新・ログ・観戦者の観測を証跡に残す記録の追加（道具の変更）をデッキリストの実装の前にするかを判断する。boundary の方式と新しいデッキでは、`HIDDEN_COUNT_KINDS` の決定（挑戦状・たまごの化石など）と、決めるのが相手の決定に届くので、その時点の相手の観測を残す価値が上がる
4. 新しい規則 6 は、今の道具の識別（`60a16e49…`）で作る計画から有効。C1・C2・99 局の保存の判定は規則 5 のまま
