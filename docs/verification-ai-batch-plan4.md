# 検証用 AI の小規模バッチの計画 4（明示的なデッキリスト・boundary・観測の記録つき）

- 状態: **推奨 12 局を採用して実行した（11 章。2026-11-12）**。18 局案は採らなかった。1〜10 章は実行の前に書いた計画のまま（そのときは対戦・seed の探索・テスト・ビルドをせず、
  `kyuura_engine`・`tools.verification_ai` を import せずに調べた）。事前確認（`decklist` コマンド・`deck_problems`・確定の `plan.json`）の結果は 11.1 節。
- 基点: `claude/vai-batch-plan3` の `060cdeb`（実装 `58fa44b`。明示的なデッキリスト・方式 boundary・観測の記録を含む公開のコミット）。origin と一致・未コミットの変更なし。
  `origin/main`（`7b3d53c`）には未取り込み（`git merge-base --is-ancestor 060cdeb origin/main` が 1）。
- 識別（読んだ値。今回は計算していない）: 計画・完了の形式 5、TOOL_VERSION 6、判定の規則 6、エンジン 0.179.0・`behavior_digest` `67c4c15b…7fca`、道具の識別 `4f97edbf…2deb`
  （[verification-ai-decklist.md](verification-ai-decklist.md) 8 章・証跡 `vai-decklist-boundary/identity_after_change.json`）。
- 目的: これまで自然な方策の実行で届いていない経路（マチスの秘策・P6・U-R3a・unverified の選択・スタジアム）を狙い、新しいバッチの機能（明示リスト・boundary・観測の記録）の使い方と
  実行の予算を決めること。到達を保証するカード別の戦略・固定の選び手は加えない。
- 機械で読める下書き: [verification-ai-batch-plan4.json](verification-ai-batch-plan4.json)（`status: draft`。実行の前の検査を通した確定の計画ではない）。

## 1. 既存の根拠の区分

| 区分 | うらのカード（マチスの秘策・P6・U-R3a） | スタジアム |
|---|---|---|
| (a) new_game からの自然な方策の実行 | **なし**。固定デッキにマチスの秘策がなく、30 局・99 局・C1・C2 で `reveal_face_down` は提示 0、P6・U-R3a の送信 0（[plan3](verification-ai-batch-plan3.md) 1.2 節・10.4 節） | **なし**。`use_stadium` は提示 0（同） |
| (b) new_game からの固定の選び手（決まった手順）による合法な操作の列 | エンジンの側の決まった手順の対戦 `--batch v0.67`（`tools/existing_effect_games.py`。`L67` と `PAIRINGS_V0_67` の 40 局。うらで出す 56 回・おもてにする 33 回・にげるでおもてにした記録なし。[secret-plan-preflight-v0.67.md](secret-plan-preflight-v0.67.md)）。クライアント API・検証用 AI の経路ではない | U7 の接続のテスト（`tests/test_legal_actions_u7_5d.py:398-440`。`LUCKY_DECK` 対 `CONNECT_DECK`・seed 1 で、play_trainer → use_stadium → end_turn を固定の選び方で送り、replay_run が成功）。ニンジャジムの合法な列（`tests/test_ninja_gym_oracle_v0_146.py`） |
| (c) 構築盤面 | P6（`fixtures_p6`・`p6-ai-follow`・`vai-p6-accepted`）、U-R3a の 3 ケース（`fixtures_u_r3a`・`u-r3a-ai-follow`。U1 ロケット団のヒトカゲの受理・U2 拒否 `WRONG_ENERGY_TYPE`・U3 フシギバナのトラッシュ）、観測の記録の p6・ur3a の fixture | U7-5d の構築盤面のテスト（`use_stadium` の段の入力） |
| (d) 模擬の応答・単体テスト | 判定の規則 4・5 の表（偽の応答）、`test_verification_ai_decklist_boundary` の boundary の範囲（偽の候補） | — |
| 静的な根拠 | R-3 の監査の 2 章（2〜3 段の特殊能力の型とカード）、P6 の文書 1.1 節（おもてにする処理の順） | [plan3](verification-ai-batch-plan3.md) 2.2 節（`use_stadium` は may_stop_later で deep の範囲に入る見込み） |

(b) の seed・手順が届いたことは、自然な方策で届くことの保証に**しない**。(c)・(d) は new_game から届いた証拠ではない。

## 2. 対象とデッキ（2 組）

デッキの中身・並び・出典・変更点を記録する。既存の固定デッキ（`kyuura_engine/decks.py`）とテスト・道具のデッキの定義は変えない。明示リストは `kyuura-vai-decklist/1` で、展開は項目の並びのまま
（`existing_effect_games.deck_cards` もテストのリストも同じ並びで作るので、下の項目の並びで元の配列と同じになる見込み。事前確認で `sha256` を照らす）。

### 2.1 A: うらのカード（推奨は `L67-U`。採用の判断が要る）

**元のデッキ** `L67`（`tools/existing_effect_games.py:1254` の `DECKS["L67"]`。トレーナーは `:858` の `TRAINERS`、展開は `:3144` の `deck_cards`。v0.67 の決まった手順の対戦で使った 60 枚）:

| # | カード ID | 名前 | 枚数 |
|---|---|---|---|
| 1 | PMCG1-052 | ディグダ | 4 |
| 2 | PMCG1-058 | エビワラー | 4 |
| 3 | PMCG1-043 | ケーシィ | 4 |
| 4 | PMCG1-046 | ユンゲラー（1 進化） | 3 |
| 5 | PMCG5-093 | マチスの秘策 | 4 |
| 6 | PMCG1-074 | マサキ | 2 |
| 7 | PMCG1-073 | ポケモンいれかえ | 2 |
| 8 | PMCG1-071 | きずぐすり | 2 |
| 9 | PMCG1-081 | プラスパワー | 2 |
| 10 | PMCG1-079 | ディフェンダー | 2 |
| 11 | PMCG1-072 | 突風 | 2 |
| 12 | PMCG1-102 | 闘エネルギー | 15 |
| 13 | PMCG1-101 | 超エネルギー | 14 |

**推奨の案** `L67-U`（検証用の明示リスト案。採用の前）: `L67` の 4 行目のあとに **PMCG1-049 フーディン（2 進化）2 枚**を入れ、13 行目の超エネルギーを **14 → 12 枚**にする（60 枚。ほかは同じ並び）。

- 変更の理由: `L67` のポケモン（ディグダ・エビワラー・ケーシィ・ユンゲラー）には特殊能力がなく、`L67` のままでは U-R3a の候補が**出ない**（静的。[plan3](verification-ai-batch-plan3.md) 2.2 節）。
  フーディンの［ダメージスワップ］は `MoveDamageCounter`（source 自分の場 → target 自分の場の 2 段。[legal-actions-r3-audit.md](legal-actions-r3-audit.md) 2 章 58 行）で、
  どちらの段の選べるものも自分の場なので、うらのフーディンが場にあれば組はいつも完成する見込み（入力が公開される）。ケーシィ → ユンゲラーの系統の上の段で、エネルギーの種類を増やさない
- うらのフーディンの特殊能力は、受理なら必ず「たねでないのでトラッシュ」（U-R3a の監査 1 章の 7a）。**「おもてにして使った」受理（A1 `TakeEnergyToSelf`。ロケット団のヒトカゲと炎エネルギーが要る）は、この案では狙わない（残す）**
- 選ばなかった案: ロケット団のヒトカゲ（PMCG4-012）を入れる案は炎エネルギーも要り、変更が大きい。フシギバナ（PMCG1-011）・カメックス（PMCG1-032）は系統がデッキになく、場で使う意味がない
- `L67-U` を採らない場合は `L67` のまま実行し、U-R3a を対象から外す（P6・マチスの秘策・unverified だけ）

**相手**: 同じリスト（ミラー）。`PAIRINGS_V0_67` の相手（C66・R65・S66・G64）は、ベンチへのダメージや［れんぞくいしなげ］で相手のうらのカードを**おもてにさせる**組として選ばれた
（`:1996` のコメント）。うらのままバトル場へ出ることが前提の P6・U-R3a には不利なので使わない。ミラーなら、両方の側にマチスの秘策があり（機会が 2 倍）、相手の突風（2 枚）が
自分のうらのカードをバトル場へ出す経路にもなる。`L67` 対 `L67` は既存の組み合わせにない（変更点として記録する）。

### 2.2 B: スタジアム（`LUCKY_DECK` 対 `CONNECT_DECK`。既存のテストのデッキのまま）

- **出典**: `tests/test_legal_actions_u7_3.py:464` の `CONNECT_DECK`（炎のポケモン 8 種 × 4 と炎エネルギー 28）と、`tests/test_legal_actions_u7_5d.py:398-406` の `LUCKY_DECK`
  （`CONNECT_DECK` の炎エネルギー 4 枚をラッキースタジアム PRN-015 の 4 枚にした 60 枚）。U7 の接続のテストの組と同じ（デッキ 0 が `LUCKY_DECK`）
- **`LUCKY_DECK` の並び**: PMCG1-014 ヒトカゲ 4・PMCG1-017 リザード 4・PMCG1-018 ガーディ 4・PMCG1-019 ウインディ 4・PMCG1-015 ロコン 4・PMCG1-022 キュウコン 4・
  PMCG1-016 ポニータ 4・PMCG1-020 ブーバー 4・PMCG1-098 炎エネルギー 24・PRN-015 ラッキースタジアム 4（`list.remove` は先頭の炎から 4 枚を除き、スタジアムは末尾に足す）
- **`CONNECT_DECK` の並び**: 同じポケモン 8 行と PMCG1-098 炎エネルギー 28
- ラッキースタジアム（PRN-015。`CoinDrawStadium`・`once_stated`。のぞむなら自分の番ごとに 1 回コイン、おもてなら 1 枚引く。[remaining-stadiums-v0.74.md](remaining-stadiums-v0.74.md) 44 行）。
  `use_stadium` の入力は空（テストは `[]` で送る）
- **選ばなかった案**: ニンジャジムのデッキ（`LEGAL_DECK`。草エネルギー 47 枚のテスト用）は、NJ1（`UNRESOLVED_NINJA_GYM_WITHOUT_TARGET`）の停止の確かめのためのデッキで、`use_stadium` の受理より
  停止に寄る。スタジアムを両方の側に入れる案（入れかえ）は、今回の目的（play_trainer と use_stadium の区別）に要らない

## 3. 到達の根拠と限界

| 対象（デッキ） | 狙う操作・入力・結果 | 必要な前提（場・手札・番・決定） | 既存の到達例（区分） | ランダム・ルール・boundary が選ぶ見込み | 方策の性質で届きにくい理由 | 今回の計測値 | 未到達でも言えること・言えないこと |
|---|---|---|---|---|---|---|---|
| マチスの秘策（A） | `play_trainer`（PMCG5-093）→ 決定 `secret_plan_card`（手札から 0〜1 枚）→ うらで出す（`secret_plan_placed`）か出さない（`secret_plan_declined`） | 自分の番の MAIN・手札に秘策・ベンチに空き・手札にほかのカード | (b) v0.67 の 56 回 | deep・boundary とも候補にあれば選びうる（rules の優先順位は play_trainer 5）。候補の処理可能性は**静的に確かめていない** | 決定の数は uniform-stage で 0 と 1 を均等に引くので、約半分は出さない | `play_trainer` のうち PMCG5-093 の提示・選択・受理、決定の答え（0・1 枚）、うらで出した数 | 少数局で選ばれなかった、とだけ言える |
| おもてにする（A） | `reveal_face_down`（`choice`）の受理 | 自分の場にうらのカード | (b) 33 回、(c) P6 の構築盤面で may_stop_later | deep の範囲に入る（may_stop_later）。rules-v2 では優先順位 5 で、ほかの 5 と均等 | おもてにすると P6・U-R3a の前提が消える。deep が先におもてにしやすい | 提示・選択・受理、`secret_plan_revealed` の `cause`（choice・attack・retreat・power） | — |
| P6（A） | うらのバトル場のポケモンの `retreat`（段に `cost_evaluation`）。受理の中身（にげた・トラッシュ）、正常な拒否（`P6_ENGINE_DECIDES`） | うらのカードがバトル場にいる（自分のポケモンいれかえ・相手の突風・きぜつのあとの交代で選ぶ）・ベンチにほかのポケモン・自分の番 | (c) だけ（v0.67 でもにげるでおもてにした記録なし） | deep は候補が unverified なので、範囲の中にほかの候補（end_turn はいつもある）があれば選ばない。boundary は区分（supported・may_stop_later・unverified）を均等に選ぶ | 前提が 2 段（うらで出す → バトル場へ移る）。移すポケモンいれかえ・突風は 2 枚ずつで、対象の選び方も均等 | P6 の候補の提示・範囲・選択・入力・check・送信・結果、`judge.accepted_content_by_check` の P6 の内訳、拒否のコード | 届かなくても、P6 の未実装・不具合の証明にしない |
| U-R3a（A。`L67-U` のときだけ） | うらのフーディンの `use_power`（2 段。`power`・`pokemon` に `face_down: true`）。受理の中身はトラッシュだけ | うらのフーディンが場（ベンチでよい）にある・自分の番 | (c) だけ（U3 はフシギバナ。フーディンの例はない） | deep は選ばない（unverified）。boundary は unverified の区分が出れば選びうる | 手札にフーディンがある番に秘策を使い、そのフーディンを選ぶ必要がある。uniform-stage の決定の選び方 | 提示・範囲・選択・入力・check・送信・結果、受理の中身（トラッシュ）、check の invalid（異常 `face_down_power_check_invalid_for_generated_input`） | 「おもてにして使った」受理（A1）は対象の外。届かなくても未実装の証明にしない |
| unverified の選択・正常な拒否（A） | boundary が unverified の候補（P6・うらの特殊能力・うらのカードのワザ）を選び、送る | 上の前提 | (c)・(d) | boundary だけ | 提示されただけでは数えない | 候補の区分（`candidate_class`）と完成した入力の区分（`input_processability`）を分けた選択・送信の数、`deep_fallback_unverified` | — |
| スタジアムを出す（B） | `play_trainer`（PRN-015。手札 → 場） | 自分の番の MAIN・手札にスタジアム・場に同じ名前のスタジアムがない | (b) U7 の接続のテスト（seed 1） | 候補にあれば deep・boundary とも選びうる。処理可能性は**静的に確かめていない** | — | `play_trainer` のうち PRN-015 の提示・選択・受理 | — |
| スタジアムを使う（B） | `use_stadium`（場のスタジアム。入力は空）→ コイン → 引く | 場にラッキースタジアム・その番にまだ使っていない | (b) 同上 | may_stop_later なので deep の範囲（[plan3](verification-ai-batch-plan3.md) 2.2 節）。rules の優先順位 5 | 1 番に 1 回。boundary は区分の均等で end_turn と競う | `use_stadium` の提示・範囲・選択・送信・受理、番ごとの回数 | `play_trainer` と `use_stadium` を混ぜて数えない |

- P6 と U-R3a は、どちらも「マチスの秘策でうらで出す」が前提で、同じデッキで狙うのは合理的（U-R3a はベンチでよく、P6 はバトル場が要る）。**優先は P6**（`L67` のままでも狙える）、
  U-R3a は `L67-U` を採ったときの対象、A1 の「使った」受理は残す
- 通常の方策で届かなかったものを、固定の選び手・内部の状態の変更・構築盤面で埋めない

## 4. 方策・規約集合・seed と局の展開

- 規約集合: 既定の `CS-KYUURA-CURRENT@1`（`sha256:9a9b95c689d86fa01a5b710984560efda3c08f4dbf1d7c6218094ac8666f3cee`）だけ。S2A・PO は加えない
- 方式（`batch.MODES`・`SUPPORTED_SETTINGS` の既存の組だけ）:
  - `rules-v2`: 方策 rules・rules の版 2・反復の抑制の閾値 2・プロファイル deep・分布 `uniform-candidate+uniform-stage`
  - `boundary`: 方策 boundary（`BoundaryPolicy`。区分を均等 → 区分の中の候補を均等。入力は uniform-stage）・プロファイル boundary・分布 `uniform-candidate+uniform-stage`
  - 混合の boundary などの未対応の組は加えない。deep の範囲・優先順位・代替・反復の抑制は変えない
- seed（今回事前に固定。結果で選び直さない。既存の計画と重ならない）:
  - A: 4001・4002・4003（新規）
  - B: **1（回帰条件）**・4001・4002（新規）。1 は U7 の接続のテストの seed（デッキ 0 の最初の番の手札にラッキースタジアムがある）。バッチは準備の選び方を方策が決めるので、同じ手札・到達は保証しない
- seed の使い方（既存）: ゲーム・方策・ホストの seed を同じ値にし、runner が主体ごとに分ける。並びは seed ごとに方式を並べる（比較の組 = デッキ・規約集合・seed）
- 単局の上限（既存の既定値のまま）: 操作 2000・受理 1000・番 200・120 秒

**推奨: 2 計画 × 2 方式 × seed 3 = 12 局**

| 計画 | game_id | デッキ 0 対 1 | 方式 | ゲーム seed | 方策 seed | ホスト seed |
|---|---|---|---|---|---|---|
| `vai-batch-d1` | g001-rules-v2-s4001 | L67-U 対 L67-U | rules-v2 | 4001 | 4001 | 4001 |
| | g002-boundary-s4001 | 同 | boundary | 4001 | 4001 | 4001 |
| | g003-rules-v2-s4002 | 同 | rules-v2 | 4002 | 4002 | 4002 |
| | g004-boundary-s4002 | 同 | boundary | 4002 | 4002 | 4002 |
| | g005-rules-v2-s4003 | 同 | rules-v2 | 4003 | 4003 | 4003 |
| | g006-boundary-s4003 | 同 | boundary | 4003 | 4003 | 4003 |
| `vai-batch-d2` | g001-rules-v2-s1 | LUCKY_DECK 対 CONNECT_DECK | rules-v2 | 1（回帰） | 1 | 1 |
| | g002-boundary-s1 | 同 | boundary | 1（回帰） | 1 | 1 |
| | g003-rules-v2-s4001 | 同 | rules-v2 | 4001 | 4001 | 4001 |
| | g004-boundary-s4001 | 同 | boundary | 4001 | 4001 | 4001 |
| | g005-rules-v2-s4002 | 同 | rules-v2 | 4002 | 4002 | 4002 |
| | g006-boundary-s4002 | 同 | boundary | 4002 | 4002 | 4002 |

1 つの計画に入るデッキの組は 1 つなので、A・B を別の計画にする。

**18 局の案（推奨しない。採るなら理由を記録する）**: A だけ seed を 4004〜4006 に足して 12 局（B は 6 局のまま）。P6・U-R3a は前提が 2 段で、6 局では 1 回も届かない可能性が高いため。
B は 1 局でも play_trainer・use_stadium の両方が出る見込みなので増やさない。12 局の結果で十分なら増やさない。

## 5. 時間・証跡量・停止方針

### 5.1 上限

| | 局 | 予算 | 次の局を始める条件 | 証跡の上限 | 局数の上限 |
|---|---|---|---|---|---|
| `vai-batch-d1` | 6 | 360 秒 | 残り ≥ 150 秒（累積 210 秒まで） | 640 MiB | 6（18 局の案では 12） |
| `vai-batch-d2` | 6 | 240 秒 | 残り ≥ 150 秒（累積 90 秒まで） | 384 MiB | 6 |
| 合計 | 12 | 600 秒（10 分） | — | 1024 MiB（1 GiB） | 最大 18 |

- 単一のプロセスで逐次（d1 のあと d2。同時に動かさない）。上限に先に達したら未着手を残して止め、延長しない
- 単局の上限と、次の局を始める予備 150 秒・証跡の予備 64 MiB は既存の値のまま
- 見込み（参考値。新しいデッキでの実測ではない）:
  - 時間: C1 は 1 局平均約 3 秒（81 秒 / 27 局）。boundary は反復の抑制がないので操作の上限（2000）まで続く局がありうる（単局 120 秒まで）。最悪でも各計画で 1〜2 局は始められる
  - 証跡: C1 は 1 局約 5.4 MB（記録なし）。観測の記録ありは約 2.2 倍・受理 1 回あたり約 33 KB で、これは**既存のテストの fixture（uniform-stage・seed 12・受理 80）での参考値**
    （[verification-ai-observation.md](verification-ai-observation.md) 8 章）。受理の上限 1000 の局では observe/ だけで約 33 MB になりうる。12 局で約 150〜450 MB の見込み（未計測）

### 5.2 停止方針（既存の既定と同じ。計画に保存する）

| 区分 | 扱い | 既存の設定 |
|---|---|---|
| known_stop | 理由ごとに保存して続ける | `on_known_stop: continue` |
| 根拠不足の既知の停止（`evidence_missing_stop`） | 理由ごとに保存して続ける | `--undetermined-evidence-missing continue` |
| `accepted_content_unrecorded` | 保存して止める | `on_undetermined` |
| 観測の記録の失敗・欠落・矛盾・要約の欠け | 保存して止める（完了マーカーは `complete_with_stop`） | `on_observation_problem: stop` |
| 未知の診断・契約の未知・no_progress・分類できない undetermined | 保存して止める | `on_undetermined` |
| suspect・異常（状態の不整合を含む）・failed | 保存して止める | `on_suspect`・`on_anomaly`・終わり方 |
| replay_run の不一致・記録の対応の問題 | 保存して止める | `on_verification_problem: stop` |
| 書き込みの失敗・adapter の例外 | 局を未完了（INCOMPLETE）として残し、セッションを止める | 既存の `stopped_<status>` |

- 停止の確かめ（`--acknowledge-stop`）は自動で外さない。止まったら、そこで報告する
- 異常が出たら対象の局を保存し、バッチ全体を無条件にやり直さない。未完了の局を新しい attempt でやり直すかは、原因を確かめてから判断する（`run` を自動で再実行しない）

## 6. 形式・事前確認・記録

- 形式 5 の新しい計画を作る。旧形式の計画・結果（B1・B2・C1・C2 など）は元の道具の版とともに残し、新しい版で再開・再集計しない
- 計画に入るもの（形式 5 の既存の項目）: 明示リストのラベル・出典・カード ID と枚数・展開の並び・`content_sha256`・実行用の配列の `sha256`・合法性の検査の結果（`legality`）、
  方策・プロファイル・分布・seed、規約集合と実装識別、全上限と停止方針、`observation.enabled: true`

### 6.1 実行の承認のあとの事前確認（今回は未実施）

1. 基点のコミット・リモート・未コミットの変更と、識別（版・`behavior_digest`・道具の識別・TOOL_VERSION・判定の規則）を記録する
2. 事前の計画を証跡（`verifier/runs/<単位>/`）に保存する
3. 明示リスト 3 つ（`L67-U`（採らないなら `L67`）・`LUCKY_DECK`・`CONNECT_DECK`）を `kyuura-vai-decklist/1` で書く（ラベル・出典は 2 章。`content_sha256` は `decklist.content_sha256` で計算）
4. `python -m tools.verification_ai.batch decklist --file <各ファイル>` で形・確認値・`deck_problems` を確かめる。**不合格ならデッキを直さず止めて報告する**
5. 展開の並びの確かめ: `L67`（`L67-U` の元）と `LUCKY_DECK`・`CONNECT_DECK` の元の配列と、明示リストの展開の `sha256` を照らす（`L67-U` は元と違うので、変更点の 2 行だけが違うことを確かめる）
6. 計画を作る（`--observation`）:
   - `python -m tools.verification_ai.batch plan --out <証跡> --batch vai-batch-d1 --engine-commit <sha> --tool-commit <sha> --seeds 4001 4002 4003 --modes rules-v2 boundary --decklist0 <L67-U> --decklist1 <L67-U> --max-games 6 --budget-seconds 360 --evidence-max-mb 640 --undetermined-evidence-missing continue --observation`
   - `… --batch vai-batch-d2 --seeds 1 4001 4002 --modes rules-v2 boundary --decklist0 <LUCKY_DECK> --decklist1 <CONNECT_DECK> --max-games 6 --budget-seconds 240 --evidence-max-mb 384 --undetermined-evidence-missing continue --observation`
7. `plan.json`・`plan.sha256` を、この文書の 4 章・5 章・下書きの JSON と照らす（game_id・seed・方式・設定の組・デッキの確認値・合法性・規約集合の確認値・上限・停止方針・observation）
8. 実行（d1 → d2）、集計、6.2 節の読み取り、証跡と公開の要約、マニフェスト

### 6.2 記録の分け方

- 詳細（デッキの中身・応答・観測の記録）は `verifier/` に、確かめた非機密の件数だけを `public/` に置く。既存の証跡を上書きしない
- 下書きの JSON（docs）と、実行の前の検査を通した確定の計画（証跡の `plan.json`）を区別する

## 7. 成果の確認方法

### 7.1 段階を分けた集計

候補の種類ごと（A は `play_trainer`（PMCG5-093 とほかを分ける）・`reveal_face_down`・`retreat`（P6 とおもて）・`use_power`（うらとおもて）・`use_attack`（うらのカードのワザ）、
B は `play_trainer`（PRN-015 とほか）・`use_stadium`）に、次を分けて数える。

| 段階 | 出どころ |
|---|---|
| 提示 | `funnel.*.offered_fetches`・`coverage.offered_kind` |
| 方策の対象に含めた・除外した（理由ごと） | `funnel.*.in_scope_fetches`・`coverage.scope_excluded`（display_only・input_withheld・processability・unbuildable） |
| 選択 | `funnel.*.selected` と、試みの記録の `candidate_class` |
| 入力の生成 | `funnel.*.build_ok`・入力を作れない理由、完成した入力の `input_processability` |
| check | `check_valid`・`check_invalid` |
| 送信 | `submitted` |
| 結果 | accepted・rejected・refused（`by_kind`）と判定 |
| P6・U-R3a の受理の中身 | `judge.accepted_content_by_check`（P6: にげた・トラッシュ。U-R3a: トラッシュ・使った） |

- 候補・選べるもの・完成した入力の処理可能性を分ける。unverified が**提示されただけ**では boundary が試したと数えない（選択・送信を数える）
- カードごとの区別（PMCG5-093・PRN-015）と `secret_plan_revealed` の `cause` は、保存した trace を読むだけのスクリプトで数える（証跡の側。方策・行動生成を動かさない）

### 7.2 観測の記録で確かめること

| 項目 | 見る場所 | A で出る見込みの場面 | B |
|---|---|---|---|
| 本人だけに見える候補・入力・診断 | 本人の閲覧用記録と相手・観戦者の記録の比べ | うらのカードの候補（`face_down: true`）・P6 の段・拒否の診断 | 引いたカード |
| 相手・観戦者へ公開されない情報 | 相手・観戦者の観測・ログにうらのカードの `card_id` がない | 秘策で出したうらのカード、突風で選ぶ相手のうらのカード | 引いたカードの中身 |
| 受理のあとの正当な公開 | 受理の更新の新しいログ | `secret_plan_revealed` のカード id（おもてにする・P6・U-R3a の受理）、トラッシュ | スタジアムを出す・コインの結果 |
| 拒否のときに新しい更新がない | 拒否の行で相手・観戦者の項目・更新・ログが増えない、前後の観測が同じ | P6 の `WRONG_RETREAT_COST` などのおもてにしたあとの拒否（本当のカードが相手に出ない） | — |
| 選べるものの数を伏せる決定・相手が答える決定 | 相手・観戦者の記録に選べるもの・数が出ない、決定待ちの主体 | `secret_plan_card`（手札から選ぶ。`HIDDEN_COUNT_KINDS` には入っていない（静的）が、選べるものは手札で本人だけ）、きぜつのあとの相手の `promote_active` | — |

- `HIDDEN_COUNT_KINDS` の決定は、A・B のどちらのデッキにも出る見込みが低い（静的。該当のトレーナーがない）。出なければ「未出現」と記録し、成り立つとは書かない
- 観測の記録の状態（`complete` 以外）は停止方針で止める（5.2 節）

### 7.3 再現と読み方

- 各局の完全な記録を replay_run で確かめる（バッチの既存の手順。局の数に足さない）
- 届かなかったことを未実装の証明にしない。完走率・少数局の勝敗を、網羅性・強さの証明にしない
- deep と boundary の差は、同じ seed でも方策で操作の列と乱数の消費が変わるので、到達の差を方策の因果的な効果と断定しない

## 8. 採用の判断が要ること

1. A のデッキ: `L67-U`（`L67` + フーディン 2 − 超エネルギー 2）を検証用の明示リストとして採るか。採らないなら `L67` のままにし、U-R3a を対象から外す
2. 相手: A はミラー（既存の組み合わせにない）、B は U7 の接続のテストの組（`LUCKY_DECK` 対 `CONNECT_DECK`）でよいか
3. seed: A は 4001〜4003、B は 1（回帰条件）・4001・4002 でよいか
4. 局数・予算: 12 局・d1 360 秒 / 640 MiB・d2 240 秒 / 384 MiB（合計 600 秒・1 GiB）。18 局の案（A に seed 3 つ追加）を採るか
5. 観測の記録を必須にすること（証跡量は未計測。5.1 節）と、停止方針（5.2 節。既存の既定）
6. 実行のときの基点（`060cdeb` か、そのときの最新の公開コミット）

## 9. 実装の変更が要るもの（推奨の実行から分離）

推奨の 12 局は、今の道具（`58fa44b`）のまま実行できる見込み（明示リスト・boundary・観測の記録・停止方針はどれも既存）。次は推奨の外。

| 項目 | 要るもの | 対象 |
|---|---|---|
| U-R3a の「おもてにして使った」受理（A1） | ロケット団のヒトカゲと炎エネルギーを入れた新しい検証用のデッキの採用 | U-R3a の受理の中身の残り |
| カードごと・観測の境界の集計 | 証跡の側の読み取りのスクリプト（リポジトリのコードは変えない） | 7.1 節・7.2 節 |
| 次の局を始める予備（150 秒）の計画ごとの指定 | `batch.py` の CLI | 計画を 3 つ以上に分けるとき |
| 観測の記録の差分化・圧縮・間引き | 道具の実装（今回はしない） | 大きな計画 |

## 10. 今回しなかったこと

- 対戦・seed の探索・テスト・ビルド・GUI・E2E・全体テスト・lockstep・状態監査
- `kyuura_engine`・`tools.verification_ai` の import（登録・盤面・合法性を実行して調べていない）
- 新しい方策・固定の選び手・judge の根拠の追加・記録の圧縮・差分化・間引き
- エンジン本体・AI のコード・GUI・renderer・カードデータ・既存の固定デッキ・規約集合・裁定・識別方式・版の変更

## 11. 実行の結果（D1・D2。2026-11-12）

利用者が推奨の 12 局を採用し、そのまま実行した。条件・局数・予算は足していない。デッキ・seed・方策・プロファイルは計画のまま（到達させるための変更はしていない）。
下書き（[verification-ai-batch-plan4.json](verification-ai-batch-plan4.json)）は確定の計画ではない。確定の計画は証跡の `plan.json` と `plan.sha256`。

### 11.1 基点・事前確認・確定の計画

- 実行コミット: `claude/vai-batch-plan3` の `76cd566`（エンジン・道具とも。実装 `58fa44b`・文書 `060cdeb` を含む。`origin/main` `7b3d53c` には未取り込み）。リポジトリのコードは変えていない
- 識別: 版 0.179.0・`behavior_digest` `67c4c15b…7fca`・`instrumentation_digest` `d3436748…146d`・TOOL_VERSION 6・道具の識別 `4f97edbf…2deb`・判定の規則 6・計画と完了の形式 5。実行のあとも同じ（`identity_after.json`）
- 規約集合: `CS-KYUURA-CURRENT@1`（`sha256:9a9b95c6…3cee`）だけ
- 明示リスト（`kyuura-vai-decklist/1`。ラベル・出典・項目は下書きのまま。`decklist --file` の結果）:

| リスト | 項目 | `content_sha256` | 展開の `sha256` | 元の配列との照合 | `deck_problems` |
|---|---|---|---|---|---|
| `L67-U` | 14 | `72690cee…0e67` | `5fb91539…c4f3` | `L67`（`existing_effect_games.deck_cards`）との差は、フーディン 2 枚の挿入と超エネルギー 14 → 12 だけ | 空（ok） |
| `LUCKY_DECK` | 10 | `4af00364…6fc0` | `857abd7d…4eb8` | テストの `LUCKY_DECK` と同じ並び | 空（ok） |
| `CONNECT_DECK` | 9 | `45b5b6c8…9bad` | `6ae10e56…d6f8` | テストの `CONNECT_DECK` と同じ並び | 空（ok） |

- 確定の計画（`--observation`）。下書き・事前確認との照合（`check_plans.json`）は問題 0。照らした項目は、game_id の並び、ゲーム・方策・ホストの seed、方式ごとの方策・プロファイル・分布、
  単局の上限、規約集合、デッキの確認値・項目・合法性・ラベル・出典、上限、停止方針、observation:

| 計画 | 局 | 上限 | `plan.sha256` |
|---|---|---|---|
| `vai-batch-d1` | 6 | 360 秒・640 MiB | `e3cba61365b230b63fb90781fb136d16ae6b5fb0f0b989de9337cf749520796a` |
| `vai-batch-d2` | 6 | 240 秒・384 MiB | `1cb4643905d27af20b67c4f547fe7165b0dfcfb8cec47cbbdac3758acc6d785f` |

### 11.2 完了・停止・時間・資源

| | D1 | D2 |
|---|---|---|
| 完了／未完了／未着手 | 6／0／0（attempt は各局 1） | 6／0／0（同じ） |
| 完了マーカー | 停止なしの完了 6 | 停止なしの完了 6 |
| 終わり方 | game_over 6 | game_over 6 |
| バッチの停止・承認・再開 | なし（1 セッション） | なし（1 セッション） |
| replay_run | 6 局とも succeeded（期待 succeeded） | 同じ |
| 受理・番 | 779・254 | 1082・390 |
| 累積の時間（予算） | 23.217 秒（360 秒） | 33.584 秒（240 秒） |
| 局の時間 | 合計 16.8 秒・中央 2.43 秒・最大 7.06 秒 | 合計 25.6 秒・中央 4.15 秒・最大 5.33 秒 |
| 自分のプロセスの最大の作業セット | 243,707,904 バイト | 226,852,864 バイト |
| 局の証跡（うち observe/） | 52,065,387 バイト（28,378,095） | 81,851,342 バイト（47,901,665） |

合計 56.8 秒（予算 600 秒）・約 128 MiB（予算 1 GiB）。観測の記録は局の証跡の 55〜59%（記録なしの部分に対して約 2.2〜2.4 倍）、受理 1 回あたり約 36 KB（D1）・44 KB（D2）。

### 11.3 判定

- D1: 送信 779 はすべて受理で expected。終わり方 6 は expected。拒否・断り・check の invalid・undetermined・suspect・known_stop・異常は 0
- D2: 送信 1082 はすべて受理で expected。ほかは D1 と同じく 0
- 観測の記録: 12 局とも `complete`（問題 0）。行の数は送信と同じ（779・1082）
- 受理の中身（P6・U-R3a。`judge.accepted_content_by_check`）: **0 件**（その送信がなかった）

### 11.4 到達: D1（うらのカード）

保存済みの記録を読むだけのスクリプト（`analyze_d.py`）で数えた。提示は主体ごとの候補の応答、範囲・選択・入力・check・送信・結果は trace、公開の出来事は観戦者の閲覧用記録から読む。
「提示」は候補の応答に含まれた回数、「選択」以降は方策が選んだ試み。

| 経路 | 方式 | 提示 | 範囲の外（理由） | 選択 | 入力 | check valid | 送信 | 受理 |
|---|---|---|---|---|---|---|---|---|
| マチスの秘策の play_trainer（提示の列は、選んだ候補の段に PMCG5-093 があった回数） | rules-v2 | 5 | — | 3 | 3 | 3 | 3 | 3 |
| | boundary | 24 | — | 15 | 15 | 15 | 15 | 15 |
| `reveal_face_down`（may_stop_later） | rules-v2 | 3 | 0 | 2 | 2 | 2 | 2 | 2 |
| | boundary | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| うらのカードへの進化（evolve。unverified・`face_down_reveal_not_evaluated`） | rules-v2 | 3 | 3（`processability:unverified`） | 0 | — | — | — | — |
| | boundary | 1 | 0 | 0 | — | — | — | — |
| P6（うらのバトル場のにげる） | 両方 | **0** | — | 0 | — | — | — | — |
| U-R3a（うらのフーディンの特殊能力） | 両方 | **0** | — | 0 | — | — | — | — |
| うらのカードのワザ | 両方 | 0 | — | 0 | — | — | — | — |

- 秘策の結果（公開のログ）:
  - うらで出した 3（rules-v2 2・boundary 1）
  - 出さなかった（0 枚の答え）4
  - ベンチがいっぱいで何もしなかった（`secret_plan_none` の `bench_full`）11（boundary だけ）
  - 決定 `secret_plan_card` の答えは 0 枚 4・1 枚 3（すべて受理）
- うらで出したカードは、マチスの秘策 2・超エネルギー 1。**フーディンはうらで出されなかった**（手札の選べるものにあった場面はある）
- 3 枚とも、出したのと同じ番に `reveal_face_down`（`cause: choice`）でおもてにされた。たねポケモンでないので、ベンチでトラッシュされた（`secret_plan_discarded`）
- 対戦の段階で、うらのカードがバトル場にあった時点は 0（ベンチだけ）。そのため P6・U-R3a・うらのカードのワザの候補は一度も提示されなかった
- ポケモンいれかえ・突風の決定（`select_pokemon`）と、きぜつのあとの交代（`promote_active`）は届いた。ただし、うらのカードがある時点では起きなかった
- unverified の候補の選択・送信は **0**（boundary は unverified の提示 1 回を選ばなかった）。拒否・正常な拒否も 0

### 11.5 到達: D2（スタジアム）

| 経路 | 方式 | 提示 | 範囲の外（理由） | 選択 | 入力 | check valid | 送信 | 受理 |
|---|---|---|---|---|---|---|---|---|
| スタジアムを手札から出す play_trainer（選んだカードはすべて PRN-015） | rules-v2 | 48 | 0 | 10 | 10 | 10 | 10 | 10 |
| | boundary | 48 | 0 | 10 | 10 | 10 | 10 | 10 |
| 場のスタジアムを使う `use_stadium` | rules-v2 | 392 | 12（`processability:unresolved_ruling`） | 81 | 81 | 81 | 81 | 81 |
| | boundary | 364 | 6（同じ） | 107 | 107 | 107 | 107 | 107 |

- `use_stadium` の受理のうち、スタジアムの持ち主でない側（スタジアムを持たない `CONNECT_DECK`）が使ったもの: rules-v2 47・boundary 56。使用はプレイヤーごと・番ごとに最大 1 回
- 使ったあとの決定はない（コインを投げ、おもてなら引く）。コインの出来事は公開のログにある
- 場のラッキースタジアムの上に、同じ名前のラッキースタジアムを出した置きかえ（`stadium_discarded` の `reason: replaced`）が 14 回（各方式 7）
- そのあと `use_stadium` が unresolved_ruling（理由 `stops_before_acceptance`）の候補として 18 回提示され、deep・boundary とも範囲の外にした
  - 候補には停止のコードが出ないので、これが RS1（`UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT`。[remaining-stadiums-v0.74.md](remaining-stadiums-v0.74.md)）かは、この記録では確かめていない
- seed 1（回帰条件）: rules-v2 の局では、プレイヤー 0 が 1 番目の番にスタジアムを出した（U7 の接続のテストと同じ時点）。boundary の局は 5 番目の番だった。到達の保証にはしない

### 11.6 deep・代替・boundary の違い

- deep（rules-v2）の代替（`deep_fallback_unverified`）は D1・D2 とも 0
  - 理由の `rule2:fallback:no_priority`（D1 41・D2 73）は、優先順位の表にない種類（決定の答えなど）だけの場面での均等の選択で、unverified の代替ではない
- unverified の候補（うらのカードへの進化）: deep は 3 回とも範囲の外にした。boundary は範囲に入れた（1）が、区分を均等に選ぶ選択で選ばれなかった
- 選んだ候補の区分は、どちらの方式も supported・may_stop_later だけ
- boundary の選択はすべて `boundary:class:…`（D1 570・D2 635）。ほかは準備の均等の選択 3（各計画）
- 完成した入力の区分（`input_processability`）は、選んだ候補の区分とは別に trace に記録された（boundary の局）。unverified の入力は 0
- 反復の抑制:
  - boundary には反復の抑制がない。D1 では、ベンチがいっぱいの時点で秘策を 11 回使った（受理・効果なし）
  - rules-v2 の反復の抑制は D1 で 18（retreat 6・use_power 12）、D2 で 0
- 同じ seed でも、方式によって操作の列と乱数の消費が変わる。到達の差を方策の因果的な効果と断定しない

### 11.7 観測の記録による確認（到達した場面だけ）

12 局の閲覧用記録（本人 2・観戦者 1）を、保存済みの記録から照らした。違反は 0。

| 項目 | 確かめたこと | 件数 |
|---|---|---|
| 記録の整合 | 次の 6 点: `files.sha256.json` と実ファイル・完了マーカーの表の確認値、observe の状態 `complete`、閲覧用記録の項目数と構造、行の連番と受理番号の連続、行と trace の送信の operation_id・主体の対応、replay_run | 12 局とも問題 0 |
| 本人だけに見える候補 | 候補の応答はその主体の記録（`actors/<主体>.jsonl`）にだけあり、応答の主体と一致する | 不一致 0 |
| うらのカードの本当のカード（秘策） | 対戦の段階のうらの場のポケモンで、本人の観測に `real`（カード id）がある。相手・観戦者の観測には、カード・カード id・名前・HP・ワザ・特殊能力がない | 本人 3・相手 3・観戦者 3 |
| うらのカード（準備） | 準備の段階でうらで置いたたねが、相手・観戦者の観測にカードを持たない | D1 相手 20・観戦者 20、D2 相手 43・観戦者 43 |
| うらで出す出来事 | `secret_plan_placed` は本人にカードがあり、相手・観戦者は `hidden.card` が null | 3・3・3 |
| 受理のあとの正当な公開 | `secret_plan_revealed`（`reveal_face_down` の受理）が、3 主体の同じ項目に同じカード id（PMCG5-093 2・PMCG1-101 1）で出る。同じ受理でトラッシュされる（印刷の文面どおり、たねでないので） | 3 |
| 決定の選べるもの | 保留中の決定の選べるものは、決める主体の観測にだけある（D1: `secret_plan_card`・`select_pokemon`・`take_prize`・`promote_active`、D2: `discard_energy`・`forced_switch`・`promote_active`・`take_prize`） | 違反 0 |
| `secret_plan_card` の数 | `HIDDEN_COUNT_KINDS` ではないので、相手・観戦者に `option_count` が見える。その値は同じ時点の決める主体の公開の手札の枚数と同じ（手札のすべてが選べるもの）で、公開の情報より多くを示さない | 14 回とも同じ |
| 相手が答える決定 | 番のプレイヤーでない主体が決める決定（`promote_active`。D2 は `take_prize` 1 も）で、選べるものが決める主体にだけある | D1 13・D2 22 の時点 |
| 選べるものの数を伏せる決定（`HIDDEN_COUNT_KINDS`） | — | **未出現**（確かめていない） |
| 拒否のときの他者への更新・本人だけの診断 | — | **未出現**（拒否 0） |
| P6・U-R3a の受理の内訳 | — | **未出現**（送信 0） |

### 11.8 言えること・言えないこと

- 言えること:
  - 明示リスト・boundary・観測の記録をそろえた形式 5 の計画が、12 局とも停止なしで完了した。replay_run・観測の記録・判定に問題はなかった
  - 次の経路は、new_game からの自然な方策の実行で届いた: マチスの秘策の使用・うらで出す・おもてにする・トラッシュ、スタジアムを出す・使う（持ち主でない側の使用を含む）
- 言えないこと: P6・U-R3a・unverified の選択・正常な拒否は、この 12 局では届かなかった。これを、未実装・不具合がないことの証明にも、届かないことの証明にもしない
- 届かなかった理由（記録から読める範囲）:
  - うらで出したカードは、すべて同じ番におもてにされた（deep・boundary とも `reveal_face_down` を選んだ）
  - うらのカードがバトル場へ移る時点がなかった
  - フーディンをうらで出す選択がなかった
- 少数局の勝敗・完走率を、網羅性・強さの証明にしない

### 11.9 次へ広げる判断材料（今回は実行しない）

- P6・U-R3a へ自然な方策で届かせるには、うらのカードが番をまたいで残り、バトル場へ移る必要がある
  - いまの方策では、うらで出した直後に `reveal_face_down`（may_stop_later。rules の優先順位 5）が選ばれやすい
  - 方策・範囲を変えずに局を増やすか、構築盤面・固定の選び手の確認（別の枠）で補うかの判断が要る
- 証跡の見込み: 観測の記録つきで 1 局平均約 9〜14 MB（局ごとは 0.8〜20 MB。12 局で約 128 MiB）
- 同じ名前のスタジアムの置きかえのあとの `use_stadium` の停止（unresolved_ruling）のコードは、候補からは読めない。確かめるなら記録を再実行して読む（別の作業）
- 正常な拒否・選べるものの数を伏せる決定・P6・U-R3a の観測の境界は、未出現のまま
- 追記（2026-11-12）: 記録とコードを読み直すと、U-R3a はバトル場を要らず、うらで出した同じ番に届きうる。P6 も、同じ番に通常のにげるでうらの控えをバトル場へ出してから届く経路があり、
  番をまたぐ必要があるのはきぜつのあとの `promote_active` の経路だけ（上の 1 つめの項目の言い方を限定する）。到達目的の方策 `reach` の仕様と最大 4 局の計画（採用待ち・未実装）は
  [verification-ai-reach-policy.md](verification-ai-reach-policy.md)

### 11.10 証跡

`C:/dev/kyuura-engine-verification-vai/` に保存した。

- `verifier/runs/vai-batch-d/`:
  - 事前計画 `00_plan.md`、`preflight.py`・`preflight.json`、`decklists/`
  - `decklist_check_*`（1 回目の文字化けの出力は `run1_decklist_check_encoding/`）、`d1_plan_*`・`d2_plan_*`
  - `check_plans.py`・`check_plans.json`、`sessions/`（実行・集計の標準出力・終了コード）
  - `analyze_d.py`・`analyze_d.json`（1 回目の `analyze_run1.json` も残す）、`identity_after.json`、`build_public.py`、`commands.txt`
- `verifier/runs/vai-batch-d1/`・`vai-batch-d2/`: 計画・台帳・各局の完全な記録・trace・判定・観測の記録・集計
- `public/runs/vai-batch-d/`・`vai-batch-d1/`・`vai-batch-d2/` の `summary.json`: 件数だけ（seed・局の識別・選択の中身・カード ID なし）
- マニフェスト: 既存の 3,231 項目を照らして不一致 0、273 項目を追加して 3,504 項目。`sha256.json` は `6d774a82…b425` から `a9bf7e83694589eff071b1921848c30800c266f622bbfc16a565e3632a56b1e7`（更新のログは証跡の外に書いた）
