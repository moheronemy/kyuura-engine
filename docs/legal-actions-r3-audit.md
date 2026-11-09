# R-3（本人のうらのカードの特殊能力のうち、入力を返さない型）の監査と最初の補完の計画

調査・設計・文書だけの作業です。エンジン・GUI・renderer・検証用 AI のコード・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別方式は変えていません。版は 0.174.0 のままです。
補完の実装・テスト・対戦の実行はしていません（9 章）。

## 0. 基点と範囲

| 項目 | 値 |
|---|---|
| 作業ブランチ | `claude/r3-face-down-power-audit`（専用の worktree `C:\dev\kyuura-engine-vai`。利用者の `C:\dev\kyuura-engine` は `main` のまま触っていない） |
| 基点（参照した文書とコードのコミット） | `443bc89b4442dd81f48c2ec87f05c37d90512472`（`origin/claude/vai-p6-follow`。P6 の実装 `ac64d39` と検証用 AI の P6 の追従を含む。`origin/main`（`88ad4d9`）には入っていない） |
| コードの版 | `kyuura_engine` 0.174.0。配布を確かめたコミットは `f7bf450580bf0d02573b4d032271be6b8e12d699`。`kyuura_engine/` は `f7bf450` から `443bc89` まで変わっていない（AI の追従は `tools/`・`tests/`・文書だけ） |
| 方法 | コード・テスト・文書を読んだ。登録の一覧は、`kyuura_engine/effects.py` のソースを Python の `ast` で構文として読んで作った（`kyuura_engine` を import していない。モジュールの読み込み・対戦・テストはしていない）。カードの段階は `kyuura_engine/data/kyuura_cards.json` を JSON として読んだ |

## 1. 今の R-3 の条件（実装から）

R-3 の候補を作るのは `legal_actions._face_down_power_candidates`（`kyuura_engine/legal_actions.py:1787`）だけです。呼ぶのは `_power_candidates`（`:1731`）で、番のプレイヤーの MAIN の候補（`:725`）だけです。
本人の場（バトル場・ベンチ）のうらのカードごとに、本当のカード（`state.printed_def`。観測の `real` と同じ値）の印刷の特殊能力を 1 つずつ見ます。

| 順 | 条件（コード） | 結果 |
|---|---|---|
| 1 | 本当のカードがポケモンでない（`:1794`） | 候補にしない（おもてにする操作は `reveal_face_down`） |
| 2 | 登録があり、`power_by_command` が偽（`:1799`。宣言しない力・反応・ワザといっしょに使う力） | 候補にしない（R-3 ではない。おもてのカードと同じ扱い） |
| 3 | 登録がない・データと合わない（`effect is None`。`:1798`・`effects.py:11006`） | `decl` が None → 入力を返さない（`not_implemented`・`unconfirmed`・R-3） |
| 4 | 登録はあるが `POWER_INPUT_STAGES` にない型（`:1803`） | 入力を返さない（R-3） |
| 5 | 宣言の段が 0 段 | 入力なし（`no_input`・`unverified`） |
| 6 | 宣言の段が 1 段で、場所が `own_pokemon`・`opponent_pokemon`・`opponent_bench`・`hand_card`（`_FACE_DOWN_POWER_DOMAINS`。`:1784`）で、選べるものが 1 つ以上 | 1 段の入力（`confirmed`。どの選べるものも `unverified`） |
| 7 | 宣言の段が 1 段だが、選べるものが 0（手札が空・相手のベンチがいないなど） | 入力を返さない（R-3。`:1805`） |
| 8 | 宣言の段が 1 段で、場所が `energy_on_source`（前の段によるもの） | 入力を返さない（R-3。今の表にない形） |
| 9 | 宣言の段が 2 段以上（`len(decl) != 1`。`:1804`） | 入力を返さない（R-3） |

- 入力を返さない候補は `residual.present` に `{"id": "R-3", "scope": "actor"}` で現れます（`_residual_present`。`:1999-2001`）。本人の応答にだけ出ます。`inputs` は `withheld`（`INPUT_BOUNDARY_UNCONFIRMED`。`:610`）、check・submit は `CANDIDATE_NOT_EXECUTABLE` か `INPUT_BOUNDARY_UNCONFIRMED` で断ります（既存のテスト `test_multi_stage_power_withholds_inputs`）
- R-3 と R-5 は、`power.face_down` で分かれます（R-5 の監査 2 章）。上の 2（反応・常時・ワザといっしょの力）は候補自体がないので、R-3 にも R-5 にも数えません。うらのバトル場のポケモンのワザといっしょに使う力は R-2 です
- 候補の作成は `check_use_pokemon_power` を呼ばず、カードをおもてにしません（`GUARANTEE_FACE_DOWN_POWER`。`:1771`）。選べるものの並びは `_power_domain`（`:1623`）が作ります（場の公開の値・本人の手札・ついているカード）
- 実装の説明（`:1791`・[U7-5fg](legal-actions-u7-5fg.md) 4.1 節）は、2 段以上を返さない理由を「2 段目の選べるものは 1 段目の確かめのあとで決まり、確かめを呼ばずに並べると全部の組をそのまま示すことになる」と書いています。下の 2〜4 章の読みでは、今の登録の 2〜3 段の型は、どの段の選べるものも公開の値・本人の手札だけで決まります。「全部の組をそのまま示す」ことは、おもてのカードの候補（確かめで組を絞る）より保証が弱いということで、秘密が漏れることではありません

### 1.1 送ったときのエンジンの順番（変えていない）

`engine.apply_command`（`engine.py:890-918`）→ `_reveal_for_action`（`:1075`）:

1. `check_command_fields`（項目の型）・段階・保留中の決定（`_require_supported_decision`）
2. 使うポケモンがうらなら、`_require_turn`・決定待ちでないことを確かめ、おもてにする（`zones.reveal_face_down`。`zones.py:82`）
3. 本当のカードが「たねポケモン」でない（`_secret_plan_keeps`。ベイビィはたね）: ついているカードといっしょにトラッシュし、受理（`resolution.after_power`）。**`source`・`target`・`energy` は読まない**（指定したうらのカードもおもてにしない。`:1099-1101` が先に返る）
4. 「たねポケモン」: `source`・`target`・`energy` のついているポケモンがうらなら `designate_face_down(can_lose=False)` でおもてにする（たねでなければ `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`）。そのあと `check_use_pokemon_power`（`engine.py:2413`。型ごとの `check_usable`）と処理
5. 3・4 の途中の拒否・停止は、コマンドごと拒否（状態・乱数・ログはもどる。おもてにしたことも公開されない）

## 2. 型の一覧（登録と入力の宣言から）

`POWER_INPUT_STAGES`（`effects.py:49831`）の 1 段以上の型と、その登録（`ast` で読んだ。同じデータのカードの登録 `SAME_DATA_CARDS_*` と、変数に置いた効果も解決した。解決できない登録 0）。

| 型（定義） | 段（項目, 場所） | 登録しているカード（段階） | 今の R-3 |
|---|---|---|---|
| `TakeEnergyToSelf`（`effects.py:9212`） | source（自分の場）→ energy（source についているカード） | `PMCG4-012` ロケット団のヒトカゲ［ほのおをもらう］（たね）`:28631` | 返さない（2 段） |
| `EnergyTransfer`（`:7797`） | source → energy（source のカード）→ target（自分の場） | `PMCG1-011` フシギバナ（2 進化）`:28477` | 返さない（3 段） |
| `MoveEnergyAmongNamed`（`:37595`） | 同上 | `neo3-045` レアコイル［でんじりょく］（1 進化）`:37891` | 返さない（3 段） |
| `ConvertBasicEnergyColor`（`:37498`） | source → energy（source のカード） | `neo3-051` ポリゴン2（1 進化）`:37889` | 返さない（2 段） |
| `AttachEnergyFromHand`（`:7886`） | energy（手札）→ target（自分の場） | `PMCG1-032` カメックス（2 進化）`:28487` | 返さない（2 段） |
| `MoveDamageCounter`（`:7982`） | source（自分の場）→ target（自分の場） | `PMCG1-049` フーディン（2 進化）`:28497` | 返さない（2 段） |
| `MoveOpponentDamageCounter`（`:8776`） | source（相手の場）→ target（相手の場） | `PMCG3-031` ゲンガー（2 進化）`:28606` | 返さない（2 段） |
| `DiscardTypeEnergyFromHand`（`:35565`） | energy（手札） | `PF1-009`・`NIP2X-001` オーダイル（2 進化）`:35943-35944` | 1 段で示す。手札が空なら返さない |
| `MoveDamageCounterToSelf`（`:8729`） | source（自分の場） | `PMCG3-028` ヤドラン（1 進化）`:28598` | 1 段で示す（自分の場はいつもある） |
| `MoveGroupCounterToSelf`（`:40647`） | source（自分の場） | `neo3-032` アンノーンB（たね）`:40928` | 1 段で示す |
| `StopOpponentBenchPowersThisTurn`（`:43592`） | target（相手のベンチ） | `neo2-050` ププリン（ベイビィ＝たね）`:43676` | 1 段で示す。相手のベンチがいなければ返さない |

ほかの静的な結果:

- 登録があり `power_by_command` が真で、`POWER_INPUT_STAGES` にない型: **0**（上の 4 の経路は、今の登録では生成されない）
- `POWER_INPUT_STAGES` の型で登録のないもの: 0
- 登録のない特殊能力を印刷したカードは `supported` が偽（`cards.py:398-402`）で、デッキの検査が `UNSUPPORTED_CARD` で断る（`deck.py:56`）。通常の対戦の手札に来ないので、上の 3 の経路は、検査を通らない構築盤面（`build_test_state` など）でだけ生成される
- 2 段以上の 7 つの型のうち、たねは `TakeEnergyToSelf`（ロケット団のヒトカゲ）だけ。ほかの 6 つ（フシギバナ・レアコイル・ポリゴン2・カメックス・フーディン・ゲンガー）は進化カードで、送ればエンジンが 1.1 節の 3 でトラッシュし、特殊能力はおこらない

### 2.1 型ごとの詳細

共通（7 つの型）: 入力に要るのは、宣言（静的な表）、本人が知る本当のカードの印刷の特殊能力（本人の知識。本人の応答にだけ出す）、各段の場所の並び（下）。今の直接のコマンドの挙動は 1.1 節。
実行の証跡: どの型も、うらのカードとして U7 から送った実行の記録はない（V3-3 の C1 はマンキーの 0 段。P6 の固定確認はにげる）。

| 型 | 段の場所が読むもの（情報源） | 他者の秘密・本当のカードへの依存 | おもてにする前後で変わる条件 | 呼び出し先（おもてにしたあと） | 既存のテスト |
|---|---|---|---|---|---|
| `TakeEnergyToSelf` | 1 段目: 自分の場のポケモンの番号（公開）。2 段目: 選んだポケモンについているカードの uid とカード id（公開。うらのポケモンについているカードも公開。`observation.py:305-318`） | なし。自分のほかのうらのカードを 1 段目に選ぶと、エンジンが指定としておもてにする（本人は本当のカードを知っている） | 受理するか（ねむり・マヒ・こんらん（うらのあいだはない。不変条件 `zones.py:91`）・1 番に 1 回・`SAME_POKEMON`・ついていない・「炎」エネルギーカードか・エナジーバーン HC10・クリスタルビーム CB1・AT1） | `check_usable`（`effects.py:9234`）→ `_require_user_not_asleep_paralyzed_confused`・`require_power_not_used`（`:7751`）・`_own_pokemon`・`_energy_card_of_type`（`:9141`）・`_require_user_attach_scope`（`:9181`） | おもて: `test_declared_entry_powers_v0_43`。うら: `test_legal_actions_u7_5g_face_down_power`（入力を返さない）・`test_legal_actions_u7_5g_residual`（R-3 が actor） |
| `EnergyTransfer`・`MoveEnergyAmongNamed` | 自分の場・ついているカード・自分の場（どれも公開） | なし | 進化カードなので、送ればいつもトラッシュ（入力を読まない） | 呼ばれない（`check_usable` まで進まない） | おもての型のテスト。うらのテストなし |
| `ConvertBasicEnergyColor` | 自分の場・ついているカード | なし | 同上 | 呼ばれない | 同上 |
| `AttachEnergyFromHand` | 本人の手札（本人の知識）・自分の場 | なし | 同上 | 呼ばれない | 同上 |
| `MoveDamageCounter` | 自分の場・自分の場 | なし | 同上 | 呼ばれない | 同上 |
| `MoveOpponentDamageCounter` | 相手の場の番号と場所（相手のうらのカードは位置だけ。`_public_pokemon`。`:1613`） | なし（相手のうらのカードの本当のカードは読まない） | 同上 | 呼ばれない | 同上 |
| 1 段・選べるもの 0（`DiscardTypeEnergyFromHand` の空の手札、`StopOpponentBenchPowersThisTurn` の相手のベンチなし） | 空の並び（公開・本人の知識） | なし | 宣言の形（1 つ選ぶ）に合う入力がない。項目を省いたコマンドは、たねならおもてにしたあと拒否（`POWER_CHOICE_MISSING` など）、たねでなければトラッシュで受理（オーダイル） | たね（ププリン）: `check_usable`（`:43592` の型） | なし |

未確認の呼び出し先: 進化カードの 6 つの型の `check_usable` は、うらのカードとして送ったときには呼ばれないので、この監査では読んでいません（おもてのカードの候補の経路で U7-5e が確かめた範囲のまま）。
`card_is_basic_in_text`（`_secret_plan_keeps`）の、カードの段階のデータからの答えは、`stage1`・`stage2` を「たねでない」と読む前提で分類しました（関数の中は読んでいない）。

## 3. 分類（A〜E）

| 分類 | 当てはまるもの | 根拠 |
|---|---|---|
| **A** 本人の知識・公開情報だけで入力を作れる | (A1) `TakeEnergyToSelf`（たね・2 段）。(A2) 進化カードの 2〜3 段の 6 つの型 | どの段の選べるものも、自分の場・ついているカード・本人の手札・相手の場の公開の位置だけで決まる（2 章）。数・並び・依存（2 段目は 1 段目のポケモンについているカード）も公開の値だけ。受理は保証しない（`unverified`）が、入力を作るのに秘密は要らない |
| **B** おもてにしたあとの判定・今使えない情報に依存する | (B1) 1 段で選べるものが 0 の場面（2.1 節の最後の行） | 宣言の形に合う入力がなく、項目を省いた送信の結果は本当のカード（たねか）で分かれる。入力の形を新しく決める必要がある |
| **C** 未裁定・未実装で実行できない | 型としては該当なし。A1 の個々の組は、おもてにしたあと HC10（エナジーバーン）・CB1・AT1・`UNSUPPORTED_SECRET_PLAN_LOST_TARGET`（自分のたねでないうらのカードを 1 段目に選んだ）で止まることがある（エンジンの既存の扱い。入力の公開の可否とは別） | 1.1 節・2.1 節 |
| **D** 監査不足で判断できない | 該当なし（下の E の経路が将来の登録で生成されたときは D として読み直す） | — |
| **E** 今の登録では生成されない保守上の経路 | (E1) 登録のない力（データと合わない力をふくむ）。(E2) `POWER_INPUT_STAGES` にない宣言する型。(E3) `energy_on_source` だけの 1 段・知らない場所 | E1: デッキの検査が断る（構築盤面でだけ生成）。E2・E3: 該当する登録が 0（2 章） |

- A2 は、入力を作れても、送れば必ずトラッシュになり特殊能力はおこりません。結果は既存の `reveal_face_down` の候補（おもてにしてトラッシュ）と同じで、違うのはログの `cause`（`power` と `choice`）だけです。API だけで選べる操作は実質的に増えません
- `unverified` を付けることは公開の許可ではありません。A の判断は「どの段の選べるものも秘密を読まずに作れる」ことによります。一方で、おもてにしたあと拒否され得ることは、A を非公開にする理由にしません（P6 と同じ考え方）

## 4. 情報源と副作用

### 4.1 候補と入力の作成が読むもの（A1 を補完したときの予定。今のコードの呼び出し先で確かめた）

| 読むもの | 呼び出し | 区分 |
|---|---|---|
| うらであること・場のポケモンの番号・場所 | `state.is_face_down`・`_field`（`legal_actions.py:1006`） | 公開 |
| 本当のカードの印刷の特殊能力・登録・宣言 | `state.printed_def`・`state.effects.power_effect`・`POWER_INPUT_STAGES` | 本人の知識（本人の応答にだけ出す）と静的な表 |
| 自分の場のポケモンの番号と公開の値 | `_power_domain(own_pokemon)` → `_public_pokemon`（`own=True` は `_pokemon_option`。うらのカードは `face_down` だけでカード id を出さない。`:995-1000`） | 公開 |
| 選んだポケモンについているカード | `_power_domain(energy_on_source)`（`:1632`）→ `state.find_pokemon`・`source.energy`・`state.cards[uid].card_id` | 公開 |
| 本人の手札（A2 の `AttachEnergyFromHand`） | `_power_domain(hand_card)` → `_card_option` | 本人の知識 |
| 相手の場の位置（A2 の `MoveOpponentDamageCounter`） | `_public_pokemon(own=False)`（相手のうらのカードは番号・場所だけ） | 公開 |

読まないもの: 相手の手札・山札・サイド、相手のうらのカードの本当のカード、エンジンの確かめ（`check_use_pokemon_power`・`check_usable`・`_probe`）。状態をおもてにする処理・状態の複製の上の試行・効果の仮実行・乱数は、入力の作成に入れません（今の 0・1 段の経路と同じ）。

- 件数・並び・依存・理由: 1 段目の件数は自分の場のポケモンの数（ついているカードのないポケモンを外すなら、ついているカードの有無も公開）。2 段目の件数はついているカードの枚数（公開）。理由はどれも `face_down_reveal_not_evaluated` で、本当のカードの結果を予告しない（D-U75-REVEAL-OUTCOME）
- 名前で解決できない呼び出し: `state.effects.power_effect` は登録表の引き（`effects.py:11006`）。`_power_domain` の中に動的な呼び出しはない。`_pokemon_option`（`:994`）は場のポケモンの番号・場所・ベンチの位置と、本人のうらのカードなら uid と `face_down`（本人の応答だけ。カード id は出さない）、おもてならカード id を読む。`_card_option`（`:985`）は手札のカードの uid・カード id・特殊エネルギーか
- 未追跡: なし（A1 の予定の経路の範囲）。A2 の型の `check_usable` は呼ばない経路なので追っていない

### 4.2 今後のテストで同じにする情報と確かめる独立性

本人の観測には `real` があるので、本人の本当のカードだけを変えた盤面は「本人の全知識が同じ双子」ではありません。確かめを 3 つに分けます。

1. **相手・観戦者への非公開**（既存の U7-5g の双子と同じ）: 本人の本当のカードだけを変えた盤面（ロケット団のヒトカゲとコラッタなど。公開の状態は同じ）で、相手・観戦者の候補・観測・ログ・更新が同じ。本人の応答は違ってよい
2. **他者の秘密への非依存**: 本人の知識（本人の観測。`real` をふくむ）を同じにし、相手の手札・山札の並び・サイド・相手のうらのカードの本当のカードだけを変えた盤面で、本人の候補・入力・check の結果が同じ
3. **本人の本当のカードへの依存の範囲**: 選べるもの・件数・並びが、本人の観測の公開の部分（場・ついているカード・手札）と宣言だけから作った参照の並びと同じ（`real` からは印刷の特殊能力と宣言だけを読む）。同じ特殊能力を持つ別のたねのカードがないので、本当のカードを変えた比べはできない（宣言から作った参照と比べる）

無副作用: 候補・inputs・check の前後で、状態・乱数・ログ・決定の番号・全員への更新が同じ（既存の `snap` の比べ）。

## 5. 複数段の入力の表現

既存の形（U7-5e の `_power_candidate`）で表せます。新しい項目は要りません。

| 型 | 段の候補を公開の値だけで作れるか | 形 | 上流で変わるもの | 組の数（P: 自分の場のポケモンの数（バトル場＋ベンチ）、E: 自分の場についているカードの合計、H: 手札、Q: 相手の場の数） | 前の段を変えたとき |
|---|---|---|---|---|---|
| `TakeEnergyToSelf`（A1） | はい | 1 段目 source、2 段目 energy に `depends_on_stage: 1`・`upstream_stages: [1]`・`options_by_choice`（1 段目の番号 → そのポケモンについているカード）、2 段目の選ぶものの `after` | 2 段目の**入力の参照**（どのカードを選べるか）。受理（タイプ・同じポケモンなど）は実行時の合法性で、候補では分けない | 完成した組は E（2 段目の番号の数も E） | 2 段目と check の結果を捨てる |
| `EnergyTransfer`・`MoveEnergyAmongNamed`（A2） | はい | 3 段。3 段目（target）は 1・2 段目によらないが、今の形どおり番号は前の段の選び方ごとに別（`after`） | 2 段目の参照だけ | E × P | 2・3 段目と check を捨てる |
| `ConvertBasicEnergyColor`（A2） | はい | 2 段（A1 と同じ形） | 2 段目の参照 | E | 同上 |
| `AttachEnergyFromHand`（A2） | はい | 2 段。2 段目（target）は 1 段目によらない | 参照は変わらない（番号だけ別） | H × P | 同上 |
| `MoveDamageCounter`（A2） | はい | 2 段 | 同上 | P × P | 同上 |
| `MoveOpponentDamageCounter`（A2） | はい | 2 段 | 同上 | Q × Q | 同上 |

- `options_by_path` は要りません（どの段も直前の段の選ぶものだけで引ける）
- 組の数はどれも小さい（場は最大 6 匹。E・H はデッキの 60 枚が上限なので、最大でも数百）。列挙の上限を新しく置く必要はないが、実装では組の数をテストで確かめる
- check（`_power_input_problem`。`:1901`）・submit（`_command`。`:660-662`）は今のまま使えます（段の数・番号・`after` の確かめ、段の順の値をコマンドの項目に置く）。エンジンの `check_use_pokemon_power` を入力の公開のために呼ぶ必要はありません。呼ぶにはおもてにする必要があり（うらのままでは本当のカードの力を探さない）、状態の複製の上でおもてにする試行は秘密依存の確かめを候補の作成に持ち込むので使いません
- 構造の組（受理を断定しない組）の扱い: 1 段目に自分自身（使うポケモン）を選ぶ組や、2 段目に炎でないカードを選ぶ組も入ります。どれも `unverified` で、エンジンがおもてにしたあと拒否します（1 段の `MoveGroupCounterToSelf` の今の扱いと同じ）。ついているカードのないポケモンは、2 段目の選べるものがないので 1 段目に出しません（構造の欠け。合法性の判断ではない）。自分の場のどのポケモンにもついているカードがなければ、今と同じく入力を返さない（R-3 のまま）

## 6. 最初の補完の単位（提案。採用待ち・未実装）

### 6.1 推奨: U-R3a　うらのカードの 2〜3 段の宣言の、構造の組の入力

- **対象**: `_face_down_power_candidates` で、宣言の段が 2〜3 段で、1 段目の場所が `_FACE_DOWN_POWER_DOMAINS`、2 段目以降が同じ集合か直前の `source` についている `energy_on_source` の型。今の登録では 2 章の 7 つの型（A1 と A2）
- **代表**: A1 の `TakeEnergyToSelf`（受理で特殊能力がおこる唯一の型）。A2 からは `EnergyTransfer`（3 段・トラッシュ）を 1 つ
- **対象外**: B1（選べるもの 0 の 1 段）、E1〜E3、R-2、R-5、PT-5e・UP-5t、記録形式、方策の改善。エンジン・宣言の表・入力の検査・submit は変えない
- **修正の範囲**: `legal_actions.py` の候補の作成だけ。0・1 段の経路は変えない。2 段以上は、選べるものの並びを宣言の場所から作り（確かめを呼ばない）、組ごとの結果をすべて `(unverified, [face_down_reveal_not_evaluated])` にして、`_power_candidate` の段・番号・`options_by_choice`・`after` の組み立てを共用する（組み立ての部分を関数に分ける。おもてのカードの経路の出力は変えない）
- **input_disclosure・processability**: `confirmed`・`unverified`（候補・段の選べるもの・`options_by_choice` の参照のすべて）。`guarantees` は `GUARANTEE_FACE_DOWN_POWER` の「0・1 段の型だけ」を「宣言の段の型（2〜3 段は構造の組）」へ直す
- **check の保証**: 段の数・番号・前の段との依存・選べるものに含まれること（構造だけ）。受理・タイプ・回数・同じポケモンかは保証しない
- **submit**: 既存の `UsePokemonPower`（段の順の値を項目に置く）。受理・拒否（状態はもどる）・トラッシュはエンジンの既存の処理
- **直接のコマンドとの一致**: A1 の受理（2 段目に炎エネルギー）・拒否（炎でないカード・自分自身）、A2 のトラッシュを、同じコマンドを直接送った結果・状態と比べる（既存の `assert_same` の形）
- **情報境界・無副作用**: 4.2 節の 3 つの確かめと、候補・inputs・check の前後の `snap` の一致、相手・観戦者への更新 0 件
- **fixture**: 構築盤面からの合法な列（`tests.test_secret_plan_v0_67` の `board`・`place`。`build_test_state` の盤面から `apply_command` でマチスの秘策を使い、ロケット団のヒトカゲをうらにしてベンチに出す。自分のベンチに炎と水のエネルギーカードのついたたねのポケモンを置く）。A2 は同じ形でフシギバナ。new_game からの到達例はない（今回は探さない）。構築盤面の結果を new_game からの到達とは書かない
- **限定のテスト**: 新しいテスト 1 モジュール（候補の形・組の数・`stage_dependency_problems` が空・受理・拒否・トラッシュ・双子 3 種・無副作用・取っ手と不正な入力）。既存の `test_legal_actions_u7_5g_face_down_power`（`test_multi_stage_power_withholds_inputs` はロケット団のヒトカゲを使うので、入力を返さない代表を B1 か構築盤面の E1 に替える）・`test_legal_actions_u7_5g_residual`（R-3 の actor の代表を同じく替える）・`test_legal_actions_u7_5e`・`test_secret_plan_v0_67` を 1 モジュールずつ。実行の上限は 1 モジュール 5 分
- **完了の基準**: 上のテストが通る、`behavior_digest` の変化を記録して版を上げる（合法手 API の出力が変わるので、P6 と同じく版の判断が要る）、R-3 の残りが B1・E1〜E3 だけになったことを文書と残件の一覧に書く
- **GUI・AI の追従**: 7 章

### 6.2 代わりの案（候補は 3 件まで）

| 案 | 中身 | 推奨しない理由 |
|---|---|---|
| U-R3a'（A1 だけ） | 2 段目が `energy_on_source` の 2 段（`source` → `energy`）の型だけに限る（`TakeEnergyToSelf` と `ConvertBasicEnergyColor`） | 型の形で分けると、同じ形の A2 の型との違いの理由が残る。宣言で決める今の方針（カード・型ごとの分岐をしない）と合わない。範囲を最小にしたいときの代案 |
| U-R3b（B1） | 1 段で選べるものが 0 の場面に、入力のない送信を示す | 宣言の形（1 つ選ぶ）と合わない入力の形を決める必要があり、結果は本当のカードで分かれる。設計の判断が先 |

## 7. GUI・検証用 AI への影響（予定。どれも今回は変えていない）

- **GUI**: 今回、GUI のリポジトリは読んでいません。P6 のときに読んだ `78c02a6`（[P6 の文書](legal-actions-p6-face-down-retreat.md) 5.1 節）と U7-5fg の 7 章からの見込みです
  - うらのカードの `use_power` に 2〜3 段が加わる。`depends_on_stage`・`options_by_choice`・`after` はおもてのカードの U7-5e の形と同じ（CORR-3 のとおり、`depends_on_stage` が指す段の選ぶもので引く必要がある）
  - 本人の画面だけ。前の段を変えたら後の段と check を捨てる。受理・拒否・トラッシュの 3 つの結果、拒否で取っ手は失効しない
  - R-3 の `residual.present`（actor）は、補完した型では現れなくなる
- **検証用 AI**（`443bc89` のコードを読んだ）
  - 行動生成は `depends_on_stage`・`options_by_choice` を扱う（`tools/verification_ai/actions.py:181-185`）ので、形の追加は要らない見込み
  - 判定: うらのカードの候補は理由に `face_down_reveal_not_evaluated` があるので、受け付ける前の確かめの保証の外（`judge.py:163-164`）。おもてにしたあとの `invalid_input` は正常な拒否、停止は規則 3 のまま。受理の中身（おもてにして使った・トラッシュ）の分け方は P6 の `judge_p6_accepted` に近い形を検討する
  - `withheld` の数・`input_withheld(R-3)` の既知の扱いが減る。deep は `unverified` を選ばない（代わりがないときだけ）。boundary の範囲に入る

## 8. 静的な監査の制限と残件

- 静的に確かめたこと: 1〜5 章のコードの条件・登録の一覧・情報源・エンジンの順番（コードとソースの構文を読んだ）
- 既存のテストが主張すること（今回は実行していない）: 0・1 段の候補と非公開・2 段の型が入力を返さないこと・受理・拒否・トラッシュの一致（`test_legal_actions_u7_5g_face_down_power`）、R-3 の actor の分類（`test_legal_actions_u7_5g_residual`）、おもての `TakeEnergyToSelf` の処理（`test_declared_entry_powers_v0_43`）
- 実行の証跡で確かめたこと: R-3 の型には、うらのカードとして送った実行の証跡はない（V3-3 の C1 は 0 段のマンキー）
- 残件: B1（設計の判断）、E1〜E3（保守の守り。将来の登録で生成されたら読み直す）、A2 の型の `check_usable` の読む先（うらのカードの経路では呼ばれない）、`card_is_basic_in_text` の中、new_game からの到達（R-3 の型をマチスの秘策でうらにして出す固定デッキはない見込みで、探していない）。R-2・R-4・R-5 の残り・PT-5e・UP-5t は別の課題
- U-R3a は採用待ちです（承認・実装済みではない）

## 9. 実施していないこと

補完の実装、テスト、ビルド、seed 探索、対戦の実行、モジュールの読み込み、GUI・E2E・全体テスト・lockstep・状態の監査はしていません。エンジン・AI のコード・版は変えていません。
