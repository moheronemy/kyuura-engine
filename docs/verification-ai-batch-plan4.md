# 検証用 AI の小規模バッチの計画 4（明示的なデッキリスト・boundary・観測の記録つき）

- 状態: **計画だけ（採用の前の案）**。対戦・seed の探索・テスト・ビルドは実行していない。`kyuura_engine`・`tools.verification_ai` を import せず、コード・文書・テストのテキストを読んで調べた。
  `decklist` コマンド・`deck_problems`・確定の `plan.json` の作成と照合は、実行の承認のあとの事前確認（6 章）に残している。**合法性の検査は未実施**。
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
