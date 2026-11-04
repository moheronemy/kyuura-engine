# ［ポイズンミスト］とどくの量の続行規約の仕様案（PO1〜PO3）

<!-- この文書は scripts/build_poison_mist_play_policy_spec.py が docs/poison-mist-play-policy-spec.json と同じ元から作る。手で直さない（--check が違いを見つける） -->

**これは仕様案です（状態 `proposal`・承認 `not_approved`）。** 規約の登録・有効化・エンジンの続行処理は加えていません。2026-11-05 の作業の指示は、この仕様案の承認・PO1〜PO3 の裁定の承認ではありません。同じ作業の SC2 の不具合の修正（v0.144）は [sc2-integrity-fix-v0.144.md](sc2-integrity-fix-v0.144.md) に分けて記録しています。

## 1. 基点と範囲

- 基点: `7548ba46b37142983414688a215f4cbdef45161e`（版 0.143.0。origin/claude/play-policy-s2a-impl（v0.143 の最後のコミット。2026-11-05 に fetch して確かめた））。S2a の実装（規約の照会・規約を当てた記録・開発用の集合）を含む公開済みのコミットが 7548ba4 だけなので、main ではなくこれを基点にした。
- `origin/main` は `816bcffb86edeb3ea713ee08818a070e036fe0a8`（v0.140 のマージ（PR #35）。v0.141〜v0.143（S1・S2a）を含まない（origin/main は 7548ba4 の祖先））。
- 作業ブランチ: `claude/sc2-integrity-poison-mist-spec`。利用者の `.claude/` はコミットに入れていません。
- kyuura: kyuura は読んでいない（この仕様は、エンジンの記録・固定した研究基準の写しの参照だけ）。変更・コミット・push をしていない。
- 読んだもの: docs/play-policy-s2a-v0.143.md・docs/play-policy-s2a-spec.md・docs/play-policy-family-plan.md / .json・docs/ruleset-mode-design.md・停止の方針の台帳・研究の対応表・docs/damage-reactions-poison-sleep-v0.119.md 5 章、effects.py の［ポイズンミスト］・どくの量（poison_check_amount・_poison_orders・poison_mist_upkeep）、procedures.py のポケモンチェック、conditions.py の poison、tests/test_damage_reactions_poison_sleep_v0_119.py。

## 2. 承認の記録

- 作業の承認: `user_agreed`（2026-11-05）。作業の進め方: SC2 の状態の整合の不具合の修正（v0.144）・PO1〜PO3 をまとめて扱う続行規約の仕様案の作成・lockstep の記録の技術課題の記録。PO1〜PO3・TK1・SC2 の裁定への承認ではなく、この仕様案の中身の承認でもない。
- この仕様案の承認: `not_approved`。この仕様案（3 規約の中身・除外・依存・実装の段階）は、利用者の採用の判断を待つ。採用まで、エンジンに登録・有効化しない（--check が登録のないことを確かめる）。

## 3. 基本方針

- 厳密側の現行集合 CS-KYUURA-CURRENT@1 と、開発用の集合 CS-KYUURA-PLAY-S2A@1 は、同じ ID・版のまま中身を変えない。PO1〜PO3 では従来どおり止まる。
- 採用されたら、新しい規約（ID@1）と、それを加えた新しい集合（新しい ID または版）で入れる。既存の集合の中身を書き換えない。
- 続行側は、採用された規約の対象の事例だけ続ける。対象でない事例・除外の事例は、続行側でも今の停止コードで止まる。
- 研究上の未解決（PO1・PO2・PO3）は未解決のまま。続行規約は研究上の解決・公式の裁定ではない。
- カード固有の読み方を、根拠なくすべてのどく・すべての持続する効果へ一般化しない（［ポイズンミスト］の規約は［ポイズンミスト］の型の効果だけ）。
- 機能不足・技術的な制限・不具合を、規約で解消したことにしない。
- 停止の例外を捕まえて無視する構造にしない。続行は、止める理由を作る分岐の手前で規約を引き、規約があれば止める理由を作らない形にする（S2a と同じ）。

## 4. 共通の原則と、一括で判断するための要約

- **P-CHECK-TIME-AMOUNT**（どくの量はポケモンチェックの時点で、性質 → 場の効果 → 受ける側の減少の順に決める）: ポケモンチェックの 2 で受ける「どく」のダメージは、その時点の場で、(1) どく状態の性質（通常の 10・ワザで決まった量・ダメージカウンターの数にかける数。p.322 の「どく状態にかかるもの」）、(2) その時点にはたらく場の効果（［ポイズンミスト］の「20ダメージになる」。いつどく状態になったかを問わない）、(3) 受けるダメージを変える効果（鋼エネルギーの「-10」）の順に決める。規約: `PC-POISON-AMOUNT-ORDER`, `PC-POISON-MIST-TARGETS`。
- **P-MIST-SOURCE-PRESENCE**（［ポイズンミスト］の効果は、使ったポケモンが場にいるあいだだけはたらく）: ［ポイズンミスト］の効果は、使ったポケモン（発生源）に結び付く（説明が、発生源のねむり・マヒ・こんらんで効果が消えると書く）。発生源が場をはなれたら効果は終わる。場にいるまま特殊能力が消えた場合（かがくへんかガス・退化など）は、この原則で決めない（別の問い）。規約: `PC-POISON-MIST-SOURCE-LEFT`。

| 規約（案） | 停止コード | 推奨 | 観測の局 |
|---|---|---|---:|
| `PC-POISON-AMOUNT-ORDER@1` どくの量を変える効果の順番 | `UNRESOLVED_POISON_CHANGE_ORDER` | 性質 → ［ポイズンミスト］→ 鋼エネルギー | 1 |
| `PC-POISON-MIST-TARGETS@1` ［ポイズンミスト］の当てはまるどく | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | ポケモンチェックの時点でどく状態のすべてのポケモンに当てはめる | 11 |
| `PC-POISON-MIST-SOURCE-LEFT@1` ［ポイズンミスト］の発生源が場をはなれたとき | `UNRESOLVED_POISON_MIST_SOURCE` | 場をはなれたら効果は終わる | 7 |

- 3 規約は互いに依存しません（requires なし）。対象の場面は重なりません。S2a の続行側に残った停止 20 局のうち 19 局が対象です（10 章）。
- 3 規約をそろえても、#power-lost・両方のきぜつ・SC2 などでは今の停止コードで止まります（完成したプレイ用の集合ではありません）。

## 5. 規約ごとの仕様

### 5.1 `PC-POISON-AMOUNT-ORDER@1` — どくの量を変える効果の順番

状態: `proposal`・承認: `not_approved`。原則: P-CHECK-TIME-AMOUNT。研究の記録: PO1（未解決のまま）。判断事項: DEC-DAMAGE-READINGS。

| 項目 | 内容 |
|---|---|
| 解決する問い | ポケモンチェックの「どく」のダメージに、量を変える効果（特殊などくの決まった量・「どくどくエキス」のカウンターの数の 2 倍・［ポイズンミスト］の「20ダメージになる」・鋼エネルギーの「-10」）が 2 つ以上当てはまり、当てはめる順番で量が変わるとき、どの順番で当てはめるか（PO1） |
| 規約の文（推奨仕様） | どく状態の性質（決まった量、またはダメージカウンターの数にかける数）で量を求め、次に［ポイズンミスト］がはたらけばその量を 20 に置きかえ、最後に受けるダメージの「-10」（鋼エネルギー）を当てはめる。この順番は、量の効果の組み合わせによらず同じ |
| 適用条件 | effects.poison_check_amount の当てはめ方（effects._poison_orders）ごとの量が 2 つ以上ある（今 UNRESOLVED_POISON_CHANGE_ORDER で止める条件そのもの） |
| 停止コード | `UNRESOLVED_POISON_CHANGE_ORDER` |
| 対象の事例 | `UNRESOLVED_POISON_CHANGE_ORDER`（full）: ［ポイズンミスト］のある組（観測 1 局: どくどくエキスと［ポイズンミスト］。20・40）と、ない組（どくどくエキスと鋼エネルギー。10・0。構築の盤面で確かめた）の両方 |
| 除外 | 性質の違うどく状態への上書き（TP3）（`UNRESOLVED_SPECIAL_POISON_OVERWRITE`）: 量の順番ではなく、どく状態をどう置きかえるかの問い（共通規約の設計案の PC-ORDER-OVERLAP の対象。この仕様では扱わない）<br>受けるダメージを変える特殊能力をどくに当てはめるか（KA1）（`UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`）: どの効果を当てはめるかの問い（PC-NON-ATTACK-DAMAGE-MODIFIERS の対象）。順番の規約に入れない |
| 厳密側 | 当てはめ方で量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_CHANGE_ORDER）。今のまま |
| 続行側 | 止めずに、規約の順番の量でどくのダメージを与える。どくのダメージの前に、ログに規約を当てたこと（convention_applied: 規約 ID・版・場面・ポケモンの番号・量）を書く |
| 依存・関係・競合 | 依存: なし。関係: PC-POISON-MIST-TARGETS, PC-POISON-MIST-SOURCE-LEFT, PC-NON-ATTACK-DAMAGE-MODIFIERS, PC-ORDER-OVERLAP。競合: なし |
| 実装箇所 | `kyuura_engine/effects.py::poison_check_amount`<br>`kyuura_engine/effects.py::_poison_orders`<br>`kyuura_engine/procedures.py::pokemon_check_poison`<br>`kyuura_engine/procedures.py::_pokemon_check_plan`<br>`kyuura_engine/procedures.py::mid_check_knockout_divergence` |
| 共通処理 / カード固有 | poison_check_amount の PO1 の分岐の手前で続行規約を引き、規約があれば規約の並び（性質 → ［ポイズンミスト］→ 鋼エネルギー）の量を返す。返す値に当てた規約を持たせ、実際のダメージの処理（pokemon_check_poison）だけが規約を当てた記録を書く（先読み・確かめは書かない） / なし（量の効果は登録の型・どく状態の性質で識別する） |
| 既存のテスト | `tests/test_damage_reactions_poison_sleep_v0_119.py::test_doubled_poison_with_mist_is_po1_and_metal_is_fixed_last`<br>`tests/test_damage_reactions_poison_sleep_v0_119.py::test_check_knockout_uses_the_same_amount` |
| 回帰テスト（完了基準） | 続行側: どくどくエキスと［ポイズンミスト］で 20、どくどくエキスと鋼エネルギーで 10、3 つで 10。convention_applied と poison_damage の amount・amount_before・multiplier・poison_mists<br>続行側: 量が 1 つに決まる組（通常のどくと鋼エネルギーなど）では規約を当てた記録を書かない（厳密側と同じログ）<br>厳密側: 同じ盤面で今と同じ HALTED（コード・理由の文・ログ・乱数）<br>ポケモンチェックの前の確かめ（きぜつの見積もり・PK1・［ずらかる］SC1・v0.144 の SC2）と実際のダメージが同じ量<br>くろこげマーカーのコインの前の確かめ（すべての結果の組）が、規約の量で確かめること |
| 現行挙動からの差 | 今止まる組だけ、止めずに規約の順番の量を与える。量が 1 つに決まる組は状態・乱数・ログとも今と同じ |
| 推奨 | 性質 → ［ポイズンミスト］→ 鋼エネルギー（p.322 が量を変えるワザの効果を「どく状態にかかるもの」（どく状態の性質）として扱うので、性質を先に決め、そのあとにはたらく場の効果、最後に受けるダメージを変える効果、という並びは、今の既存の扱い（特殊などく・［ポイズンミスト］は鋼エネルギーより先）を延ばしたもの。組ごとの例外がない） |
| 代替案 | ［ポイズンミスト］を先、かける数をあと（どくどくエキスと［ポイズンミスト］で 40）（「20ダメージになる」を基本の量の置きかえとして読む読み方）<br>鋼エネルギーをかける数より先（どくどくエキスと鋼エネルギーで 0）（受ける側の効果を先に当てる読み方。今の既存の扱い（性質の量は鋼エネルギーより先）と合わない）<br>［ポイズンミスト］のある組だけを規約にし、ない組（どくどくエキスと鋼エネルギー）は止める（観測のない組を対象から外す（事例を分ける）） |
| 未確認 | 特殊などく 30（neo2-010 のさんばいどく）と［ポイズンミスト］の組で今 PO1 になることは、コード（_poison_orders）を読んで確かめただけ（盤面は作っていない）<br>公式資料に順番の記述がないことの再確認（研究上は未解決のまま） |

具体化した点:

- **今の量の扱い（変えない部分）**: 特殊などく・［ポイズンミスト］は鋼エネルギーより先（v0.78 からの既存の扱い。effects._poison_orders の並べかえの制限）。この規約はそれを含む全体の順番を 1 つに決める。
- **組ごとの結果**: どくどくエキス（10 × 2）と［ポイズンミスト］: 20。特殊などく 30（さんばいどく）と［ポイズンミスト］: 20。どくどくエキスと鋼エネルギー: 20 − 10 = 10。どくどくエキス・［ポイズンミスト］・鋼エネルギー: 10。特殊などくとかける数は同時に持たない（上書きは TP3 で止める）。
- **「〜になる」の読み方**: ［ポイズンミスト］の「受ける「どく」のダメージは、20ダメージになる」を、どく状態の性質で決まった量を置きかえる場の効果として読む（性質の量に重ねて倍にしない）。かける数（「どくどくエキス」の「のせるダメージカウンターの数が、2倍になる」）は、どく状態の性質（p.322 の「どく状態にかかるもの」）として先に当てはめる。
- **0 以下**: 鋼エネルギーの「-10」で 0 になる量は 0（今の energy_received_damage のまま。負にしない）。
- **［ポイズンミスト］の当てはまる相手**: PC-POISON-MIST-TARGETS（PO2）・PC-POISON-MIST-SOURCE-LEFT（PO3）が決める。この規約は、当てはまると決まったあとの順番だけ。

### 5.2 `PC-POISON-MIST-TARGETS@1` — ［ポイズンミスト］の当てはまるどく

状態: `proposal`・承認: `not_approved`。原則: P-CHECK-TIME-AMOUNT。研究の記録: PO2（未解決のまま）。判断事項: DEC-TEXT-READINGS。

| 項目 | 内容 |
|---|---|
| 解決する問い | ［ポイズンミスト］の「「どく」状態になったポケモン」に、この力を使う前からどく状態だったポケモンも当たるか（PO2） |
| 規約の文（推奨仕様） | ［ポイズンミスト］の効果は、ポケモンチェックの時点でどく状態のすべてのポケモン（お互いの場。いつ、何でどく状態になったかを問わない）が受ける「どく」のダメージに当てはまる |
| 適用条件 | effects.poison_check_amount で、使う前からどく状態だったポケモン（PoisonMist.poisoned_before）に当てはめるかで量が変わる（今 UNRESOLVED_POISON_MIST_EARLIER_POISON で止める条件そのもの） |
| 停止コード | `UNRESOLVED_POISON_MIST_EARLIER_POISON` |
| 対象の事例 | `UNRESOLVED_POISON_MIST_EARLIER_POISON`（full）: 観測 11 局はどれも、使う前からの通常のどく（10）が［ポイズンミスト］で 20 になるかの組 |
| 除外 | 使ったポケモンが場をはなれた記録（`UNRESOLVED_POISON_MIST_SOURCE#source-left`）: はたらくかは PC-POISON-MIST-SOURCE-LEFT が決める（この規約は、はたらく記録が当てはまる相手だけ） |
| 厳密側 | 当てはめるかで量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_MIST_EARLIER_POISON）。今のまま |
| 続行側 | 止めずに、使う前からどく状態だったポケモンにも当てはめた量を与える。どくのダメージの前に convention_applied（規約 ID・版・場面・ポケモンの番号・量・記録の発生源） |
| 依存・関係・競合 | 依存: なし。関係: PC-POISON-AMOUNT-ORDER, PC-POISON-MIST-SOURCE-LEFT。競合: なし |
| 実装箇所 | `kyuura_engine/effects.py::poison_check_amount`<br>`kyuura_engine/effects.py::CoinPoisonMistUntilNextTurn`<br>`kyuura_engine/conditions.py::poison`<br>`kyuura_engine/procedures.py::pokemon_check_poison` |
| 共通処理 / カード固有 | poison_check_amount の PO2 の分岐の手前で続行規約を引き、規約があれば「当てはめる」読み方の量を返す（PO1 と同じ返し方・記録の書き方） / ［ポイズンミスト］の型（CoinPoisonMistUntilNextTurn）の記録だけ。ほかの持続する効果へ広げない |
| 既存のテスト | `tests/test_damage_reactions_poison_sleep_v0_119.py::test_earlier_poison_is_po2_only_when_the_amount_differs`<br>`tests/test_damage_reactions_poison_sleep_v0_119.py::test_new_poison_takes_twenty` |
| 回帰テスト（完了基準） | 続行側: 使う前からの通常のどく（自分の場・相手の場）が 20。convention_applied と poison_damage の poison_mists<br>続行側: 使ったあとのどく・使う前からの特殊などく 20 では規約を当てた記録を書かない<br>厳密側: 同じ盤面で今と同じ HALTED<br>保存（形式 35）・観測・clone・pickle のあとに同じ量（記録 poisoned_before は変えない） |
| 現行挙動からの差 | 今止まる場面だけ、止めずに 20 を与える |
| 推奨 | ポケモンチェックの時点でどく状態のすべてのポケモンに当てはめる（文に原因・時点の限定がなく、効果の対象が「ポケモンチェックで受けるどくのダメージ」なので、ポケモンチェックの時点の状態で決める読み方が文に近い。履歴（いつどく状態になったか）を使わずに決まり、量の規約（PC-POISON-AMOUNT-ORDER）と同じ原則（時点で決める）になる） |
| 代替案 | 使ったあとに新しくどく状態になったポケモンだけ（今の poisoned_before で外す）（「なった」を変化（使ったあとにどく状態になった）として読む読み方） |
| 未確認 | 公式資料・カードの解説に、使う前からのどくについての記述がないことの再確認（研究上は未解決のまま） |

具体化した点:

- **「なった」の読み方**: 「「どく」状態になったポケモン」を、ポケモンチェックの時点でどく状態であるポケモンとして読む。p.322 の例（「このワザによって、どく状態になったポケモンが…」）は「このワザによって」で原因を限るが、［ポイズンミスト］の文には原因・時点の限定がない。
- **記録 poisoned_before**: 状態の記録はそのまま（厳密側が使う）。続行側の量の判断では使わない。
- **使ったあとに回復して、またどく状態になったポケモン**: 今も「使ったあとのどく」（conditions.py が poisoned_before から外す）。規約のもとでも同じ 20。
- **量が同じ組**: 使う前からの特殊などく 20 は、当てはめても量が同じなので今も止めない（規約を当てた記録も書かない）。
- **どくの量の順番**: 当てはまると決まったあとの量は PC-POISON-AMOUNT-ORDER の順番（この規約だけを採るなら、順番で量が変わる組は PO1 で止まる）。

### 5.3 `PC-POISON-MIST-SOURCE-LEFT@1` — ［ポイズンミスト］の発生源が場をはなれたとき

状態: `proposal`・承認: `not_approved`。原則: P-MIST-SOURCE-PRESENCE。研究の記録: PO3（未解決のまま）。判断事項: DEC-LASTING-READINGS。

| 項目 | 内容 |
|---|---|
| 解決する問い | ［ポイズンミスト］を使ったポケモンが場をはなれたあとも、「次の自分の番の始めまで」の効果が続くか（PO3 のうち、発生源が場にいない場合） |
| 規約の文（推奨仕様） | ［ポイズンミスト］を使ったポケモンが場をはなれたら（きぜつ・手札や山札にもどる・トラッシュなど）、その記録の効果は終わる（そのあとのポケモンチェックで当てはめない）。場にいるまま特殊能力が消えた記録（かがくへんかガス・退化など）は、この規約の対象外 |
| 適用条件 | effects.poison_check_amount で、中断の印（PoisonMist.interrupted）のある記録の効果が続くかで量が変わり（今 UNRESOLVED_POISON_MIST_SOURCE で止める条件）、その記録の発生源の番号のポケモンが今場にいない |
| 停止コード | `UNRESOLVED_POISON_MIST_SOURCE` |
| 対象の事例 | `UNRESOLVED_POISON_MIST_SOURCE#source-left`（full）: 台帳にまだない事例（proposed_cases）。観測 7 局はどれもこの事例（使ったポケモンが、同じ番にガスばくはつの自分へのダメージできぜつした） |
| 台帳に加える事例（案） | `UNRESOLVED_POISON_MIST_SOURCE#source-left`: 中断の印のある［ポイズンミスト］の記録の発生源（pokemon_id）のポケモンが、ポケモンチェックの時点で場にいない<br>`UNRESOLVED_POISON_MIST_SOURCE#power-lost`: 中断の印のある［ポイズンミスト］の記録の発生源のポケモンが、ポケモンチェックの時点で場にいる（かがくへんかガス・退化・姿の変化で特殊能力が消えた、または消えたあともどった） |
| 除外 | 発生源が場にいるまま特殊能力が消えた記録（`UNRESOLVED_POISON_MIST_SOURCE#power-lost`）: 「その効果も消える」をねむり・マヒ・こんらん以外の力の消え方へ広げるかの別の問い（v0.117 の QK1 と同じ形）。観測 0 局。続行側でも今のまま止める（9 章の選択肢 OC-PO-4）<br>ほかのカードの持続する効果の発生源の変化（かみつく・くろいまなざしなど）（`UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED`）: 共通規約の設計案の PC-LASTING-SOURCE-CHANGE（proposal）の対象。この規約は［ポイズンミスト］の型だけで、候補を採用したことにしない |
| 厳密側 | 続くかで量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_MIST_SOURCE）。今のまま（事例を分けても止め方・コードは同じ） |
| 続行側 | 発生源が場にいない記録は当てはめずに量を決め、止めない。どくのダメージの前に convention_applied（規約 ID・版・場面・ポケモンの番号・量・終わった記録の発生源）。発生源が場にいる記録（#power-lost）で量が変わるなら、続行側でも今の停止コードで止める |
| 依存・関係・競合 | 依存: なし。関係: PC-POISON-MIST-TARGETS, PC-POISON-AMOUNT-ORDER, PC-LASTING-SOURCE-CHANGE。競合: なし |
| 実装箇所 | `kyuura_engine/effects.py::poison_check_amount`<br>`kyuura_engine/effects.py::poison_mist_upkeep`<br>`kyuura_engine/effects.py::poison_mist_working`<br>`kyuura_engine/procedures.py::pokemon_check_poison` |
| 共通処理 / カード固有 | poison_check_amount の PO3 の分岐を、中断した記録ごとに事例（source-left・power-lost）へ分け、source-left の事例だけ続行規約を引く。事例の判定は、記録の発生源の番号が今場にいるか（新しい状態の項目は要らない） / ［ポイズンミスト］の型（CoinPoisonMistUntilNextTurn）の記録だけ |
| 既存のテスト | `tests/test_damage_reactions_poison_sleep_v0_119.py::test_source_suppressed_is_po3`<br>`tests/test_damage_reactions_poison_sleep_v0_119.py::test_ends_on_status_and_expires_at_the_next_own_turn` |
| 回帰テスト（完了基準） | 続行側: 使ったポケモンがきぜつした（ガスばくはつ・ワザのダメージ）・手札にもどった盤面で、記録を当てはめずに量が決まる。convention_applied<br>続行側: 場にいるまま特殊能力が消えた（かがくへんかガス・退化）盤面は、今と同じ UNRESOLVED_POISON_MIST_SOURCE（#power-lost）<br>続行側: 場をはなれた記録と、はたらく記録が両方ある盤面<br>厳密側: どちらの事例も今と同じ HALTED<br>台帳の事例を 2 つに分けたあと、同梱の場面の一覧と照会（事例を渡す）が合うこと |
| 現行挙動からの差 | 今止まる場面のうち、発生源が場にいない記録だけ、止めずに当てはめない量を与える |
| 推奨 | 場をはなれたら効果は終わる（説明が効果の終わりを発生源の状態（ねむり・マヒ・こんらん）に結び付けているので、発生源のいない効果を続けるより、発生源とともに終わる読み方が文の作りに近い。共通規約の設計案の PC-LASTING-SOURCE-CHANGE の推奨（場をはなれたら終わる）とも合う） |
| 代替案 | 発生源によらず、次の自分の番の始めまで続く（効果を場の記録とみなし、説明に書かれた終わり方（期限・特殊状態）だけで終える読み方）<br>場にいるまま特殊能力が消えた記録（#power-lost）も同じく終わる（「その効果も消える」を力が使えなくなるすべての場合へ広げる読み方。観測がなく、QK1 と同じ問いを先に決めることになる） |
| 未確認 | 公式資料・カードの解説に、使ったポケモンが場をはなれたときの記述がないことの再確認（研究上は未解決のまま）<br>#power-lost の盤面（かがくへんかガス）は既存のテストで止まることを確かめた。退化・姿の変化の盤面は作っていない |

具体化した点:

- **「場をはなれた」の判定**: ポケモンチェックの時点で、記録の発生源の番号（pokemon_id）のポケモンが場にいない。場のポケモンの番号は場に出るたびに新しくなるので、同じカードがもう一度場に出ても、もとの記録の発生源ではない。
- **中断の印の扱い**: 今の poison_mist_upkeep の印（一度書いたら消さない）はそのまま。続行側の量の判断で、場にいない発生源の記録を「はたらかない」として扱う（状態を変えない）。
- **記録を消すか**: 推奨は、状態を変えない（量の判断で使わないだけ。記録は使ったプレイヤーの次の番の始めに今どおり消える）。厳密側と続行側で状態の形が同じになり、保存・観測が変わらない。
- **観測した局の形**: 7 局とも、マタドガスが［ポイズンミスト］を使い、同じ番にガスばくはつ（自分にも 30）できぜつし、かわりに出てきた相手の対戦ポケモンがどく状態になった。6 局はその番の終わり、1 局は相手の番の終わりのポケモンチェックで止まった。規約のもとでは、かわりに出てきたポケモンのどくは 10。
- **発生源が 2 匹以上**: 記録ごとに判断する。場にいる発生源の記録がはたらけば、量はそれで決まる（2 つ以上の記録は足さない。今のまま）。
- **PO2 との関係**: 場にいない発生源の記録は当てはめないので、その記録について PO2 の問いは起こらない。はたらく記録の当てはまる相手は PC-POISON-MIST-TARGETS。

## 6. 共通化しない問い

| 問い | 場面 | 分ける理由 |
|---|---|---|
| 発生源が場にいるまま特殊能力が消えた［ポイズンミスト］の記録が続くか | `UNRESOLVED_POISON_MIST_SOURCE#power-lost` | 力の消え方（かがくへんかガス・退化・姿の変化）ごとに読み方が分かれうる、QK1 と同じ形の問い。観測 0 局。この仕様案では止めたまま |
| 受けるダメージを変える特殊能力（カブトアーマーなど）をどくに当てはめるか（KA1） | `UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER` | どの効果を当てはめるかの問い。ワザ以外のダメージ全体の規約（PC-NON-ATTACK-DAMAGE-MODIFIERS）で扱う |
| 性質の違うどく状態への上書き（TP3）・キョウのどくの順番 | `UNRESOLVED_SPECIAL_POISON_OVERWRITE` | どく状態を与える側の順番・上書きの問い（PC-ORDER-OVERLAP の対象）。ポケモンチェックの量の規約に入れない |
| 「どくをだす」でどく状態にする相手（PX1） | `UNRESOLVED_SECRETE_POISON_TARGET` | ワザの対象の文の読み方。どくの量の問いではない |

## 7. S2a のポケモンチェック・きぜつ判定との関係

- **ポケモンチェックの順番**: どくの量は 1 のあとの場で求める（今の _pokemon_check_plan）。3 規約は、その量の決め方だけを変え、1・2 の処理の順番・きぜつの判定の時点（PC-CHECK-KO-POINT）を変えない。
- **PC-CHECK-KO-POINT（きぜつ判定）**: 2 のあとの HP 以上の判定に使う量が、規約の量になる。PK1 の違いの判定（mid_check_knockout_divergence）も同じ問い合わせの量を使うので、規約の有無で判定がずれない。
- **PC-CHECK-SIDE-ORDER（両側のコイン）**: くろこげマーカーのコインの前の確かめ（すべての結果の組）が、規約の量で確かめる。規約で PO1〜PO3 の停止がなくなると、コインの前に止まる組が減る。
- **v0.144 の SC2 の確かめ**: 2 のあとにきぜつするポケモンの判定に規約の量を使う（同じ問い合わせ）。きぜつの処理で［ずらかる］の力がもどるなら、続行側でも今どおりダメージの前に SC2 で止める。
- **両方のきぜつ**: 規約の量で両方のプレイヤーのポケモンが HP 以上になるなら、続行側でも今どおり UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT で止める（S2b の候補。この仕様の対象外）。

## 8. 状態・保存・ログ・集合

- **状態**: 新しい状態の項目はない（記録 PoisonMist の poisoned_before・interrupted と、どく状態の性質は今のまま）。
- **保存**: 書き出しの形式は 35 のまま。厳密側・続行側で同じ形。
- **ログ**: 規約を当てたときだけ、ポケモンチェックのどくのダメージ（poison_damage）の前に convention_applied を書く（規約 ID・版・場面・停止コード・ポケモンの番号 pokemon_id・量 amount・当てた／終わった記録の発生源 records）。conventions.APPLIED_FIELDS に amount・records を加える。先読み・確かめ・拒否したコマンドは書かない（S2a と同じ）。
- **観測**: convention_applied は公開の記録（S2a と同じ）。新しい非公開の情報はない（量・記録・場・どく状態はどれも公開）。
- **監査**: tests/log_audit.py の s2a_problems と同じ形の独立な確かめ（規約の表を監査が別に持つ）: 当たる場面の数・量・記録の発生源がログから組み立てた値と合うこと。
- **厳密側**: `CS-KYUURA-CURRENT@1`。変更: なし（同じ ID・版・中身）。
- **既存の開発用の集合**: `CS-KYUURA-PLAY-S2A@1`。変更: なし（同じ ID・版・中身。S2a の 5 規約だけ）。
- **続行側（案）**: `CS-KYUURA-PLAY-PO@1`（development・halts_at_undecided）。規約: CS-KYUURA-PLAY-S2A@1 の規約（今の集合の 12 件と S2a の 5 件）と、採用した PO の規約（3 件まで）。採用された規約だけを layer continuation・approval user_agreed で登録する。採用されなかった規約は登録しない（部分的な採用なら、その規約だけの集合にする）。すべての未決場面で止まらない完成したプレイ用の集合ではない（ほかの未決場面では今の停止コードで止まる）。
- **版**: 既存の集合の中身を変えない。PO の規約を加えた集合は新しい ID で作る（集合の ID の S2A は S2a の 5 規約の意味を持つので、版を上げて加えない）。

## 9. 判断が残る選択肢

| ID | 規約 | 問い | 推奨 | 代替案 |
|---|---|---|---|---|
| OC-PO-1 | `PC-POISON-AMOUNT-ORDER` | 量を変える効果の順番 | 性質 → ［ポイズンミスト］→ 鋼エネルギー | ［ポイズンミスト］→ かける数 → 鋼エネルギー（40）<br>鋼エネルギーをかける数より先<br>［ポイズンミスト］のない組は止める |
| OC-PO-2 | `PC-POISON-MIST-TARGETS` | 使う前からのどくに当てはめるか | 当てはめる（時点の状態で決める） | 使ったあとに新しくどく状態になったポケモンだけ |
| OC-PO-3 | `PC-POISON-MIST-SOURCE-LEFT` | 発生源が場をはなれたら効果が終わるか | 終わる | 期限まで続く |
| OC-PO-4 | — | 発生源が場にいるまま特殊能力が消えた記録（#power-lost） | この仕様では扱わない（続行側でも止める） | 終わる（OC-PO-3 と同じ）<br>続く |
| OC-PO-5 | — | 集合の名前と、部分的な採用 | 新しい ID CS-KYUURA-PLAY-PO@1 に、採用した規約だけを加える | CS-KYUURA-PLAY-S2A の版を上げる（ID の意味が S2a の 5 規約からずれる）<br>3 規約がそろうまで登録しない |
| OC-PO-6 | — | 規約を当てたことをログに残すか | 残す（convention_applied。S2a と同じ） | 残さない |

実装の段階:

| 段階 | 内容 | 対象 | 前提 | 厳密側の不変条件 | 続行側の完了条件 |
|---|---|---|---|---|---|
| PO-0 | 事例の分割と照会の接続 | 台帳の事例 UNRESOLVED_POISON_MIST_SOURCE#source-left・#power-lost<br>poison_check_amount の照会（事例を渡す）<br>APPLIED_FIELDS・監査の表 | この仕様案の採用 | 厳密側で、全体のテスト・lockstep・旧バッチが基点と同じ（停止コード・理由の文・ログ） | 規約の登録の前に、続行側の集合でも今と同じに止まる |
| PO-1 | 量の規約（PO1・PO2） | PC-POISON-AMOUNT-ORDER<br>PC-POISON-MIST-TARGETS | PO-0 | 厳密側のポケモンチェックの停止・ログ・乱数が今と同じ | PO1・PO2 の盤面で規約の量を与え、convention_applied を書く |
| PO-2 | 発生源の規約（PO3 の source-left） | PC-POISON-MIST-SOURCE-LEFT | PO-0 | 同上 | 場にいない発生源の記録を当てはめない。#power-lost は止まる |
| PO-3 | 計測と文書 | 新しい集合 CS-KYUURA-PLAY-PO@1 | PO-1<br>PO-2 | 全体のテスト（1 並列・モジュールごとに 1 プロセス）・lockstep・旧バッチ・延長戦が基点と同じ | 10 章の計測を記録する（完走を保証しない） |

## 10. 観測した局と計測の計画

- 元: docs/play-policy-s2a-v0.143.md 8 章（4,356 局。続行側 CS-KYUURA-PLAY-S2A@1 の停止 20 局）。対象 19 局、対象外 UNSUPPORTED_TRANSFORM_COPIED_POWER 1 局（v0.49 A49-D49 seed 2。エンジンの未対応で、規約の対象にしない）。
- 今回は一括の計測を繰り返さない（作業の指示）。19 局の内訳は、計測の記録の局を続行側の集合でやり直して確かめた（停止コード・止まった番・記録・発生源の場の有無）。

| バッチ | 組 | 席（先に書いた方がプレイヤー 0） | seed | 停止コード | 事例 | 規約（案） |
|---|---|---|---:|---|---|---|
| v0.119 | P119-D119 | P119 対 D119 | 1 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-D119 | P119 対 D119 | 2 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-D119 | P119 対 D119 | 3 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-D119 | D119 対 P119 | 0 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-D119 | D119 対 P119 | 1 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-D119 | D119 対 P119 | 2 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-W119 | W119 対 P119 | 0 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-W119 | W119 対 P119 | 2 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-W119 | W119 対 P119 | 3 | `UNRESOLVED_POISON_CHANGE_ORDER` | `UNRESOLVED_POISON_CHANGE_ORDER` | `PC-POISON-AMOUNT-ORDER` |
| v0.119 | P119-G119 | P119 対 G119 | 2 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-G119 | G119 対 P119 | 2 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-G119 | G119 対 P119 | 3 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-P31 | P119 対 P31 | 0 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.119 | P119-P31 | P119 対 P31 | 3 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-P31 | P31 対 P119 | 1 | `UNRESOLVED_POISON_MIST_SOURCE` | `UNRESOLVED_POISON_MIST_SOURCE#source-left` | `PC-POISON-MIST-SOURCE-LEFT` |
| v0.119 | P119-P31 | P31 対 P119 | 2 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.125 | W125-P119 | W125 対 P119 | 1 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.125 | W125-P119 | W125 対 P119 | 2 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |
| v0.125 | W125-P119 | P119 対 W125 | 1 | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `UNRESOLVED_POISON_MIST_EARLIER_POISON` | `PC-POISON-MIST-TARGETS` |

- `UNRESOLVED_POISON_MIST_EARLIER_POISON`: 使う前からの通常のどく（10）。当てはめれば 20、当てはめなければ 10。
- `UNRESOLVED_POISON_MIST_SOURCE`: 使ったマタドガスが同じ番のガスばくはつできぜつ（発生源は場にいない）。かわりに出てきたポケモンのどくが 20 か 10 か。
- `UNRESOLVED_POISON_CHANGE_ORDER`: どくどくエキス（× 2）のどくと［ポイズンミスト］。当てはめ方で 20・40。

計測の計画:

- 実装の段階（PO-3）で、全 108 バッチ・seed 0〜3（4,356 局）を、CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・新しい集合の 3 つで走らせる（組・席・seed は選び直さない）。
- 厳密側と CS-KYUURA-PLAY-S2A@1 は v0.143 の記録（v0.144 の SC2 の修正の差があればその局）と同じであること。
- 新しい集合で、19 局の停止がなくなること・続けたあとにどの停止へ着くか・規約ごとの当たった局と回数・最初の差が convention_applied であること（ログのやり直しで比べる。lockstep の記録は集合を持たない: v0.144 の文書の技術課題）。
- 実装の前に、対象の経路を通るバッチ（v0.119・v0.125）を先に走らせ、対象を通らないバッチの成功を規約の確かめに数えない。

## 11. 確かめたこと（実行した確認と、読んだだけの確認）

- python scripts/build_poison_mist_play_policy_spec.py --check: problems=0（終了コード 0）。
- わざと壊した仕様案（存在しない場面・対象の漏れ・規約の重なり・承認済みにした仕様・登録した規約・観測の局の数の違い）を --check が見つける: tests/test_poison_mist_play_policy_spec.py。
- 19 局のやり直し（計測の記録の組・席・seed を、続行側の集合 CS-KYUURA-PLAY-S2A@1 で new_game から進めた）: 停止コードが記録と同じ。PO3 の 7 局は発生源の番号のポケモンが場にいない（ガスばくはつのきぜつ）、PO2 の 11 局は使う前からの通常のどく、PO1 の 1 局はどくどくエキスと［ポイズンミスト］（20・40）。
- 構築の盤面: どくどくエキスのどくに鋼エネルギーをつけた盤面（［ポイズンミスト］なし）で、今 UNRESOLVED_POISON_CHANGE_ORDER（10・0）になる。
- 既存のテスト tests/test_damage_reactions_poison_sleep_v0_119.py（PO1〜PO3 の今の止め方）: 終了コード 0。

読んだだけ・走らせていないもの:

- 規約のもとでの量・ログ・監査は、実装していないので実行していない（仕様案）。
- 全体の対戦テスト・lockstep・一括の計測は、この仕様案のためには走らせていない（v0.144 の修正の検証は版の文書）。

## 12. 未確認

- 3 規約とも、公式資料に記述がないことの再確認はしていない（研究上の未解決は未解決のまま。続行規約は研究上の解決ではない）。
- kyuura の記録は、固定した研究基準の写し・エンジンの記録の参照だけ（kyuura を読み直していない）。
- 特殊などく 30 と［ポイズンミスト］の PO1 は、コードを読んで確かめただけ。
- #power-lost の退化・姿の変化の盤面、発生源が 2 匹以上の盤面は作っていない。
- 続けたあとにどの停止へ着くか（局の数）は、実装と計測のあとでしか分からない。

## 13. 採用のあとの経過（v0.145）

- 採用: `user_agreed`（2026-11-05）。利用者の指示「方針を採用します。」と、その依頼の採用仕様。この指示と、その依頼に書いた具体的な採用仕様（3 規約の対象・処理・除外・複数の発生源の扱い）。続行側の開発用の部分的な集合の規約の採用で、公式の裁定・エラッタ・kyuura の研究上の解決ではない。厳密側の集合・S2a の集合・#power-lost・ほかの未決の場面は変えない。
- 実装: 版 0.145.0（docs/poison-mist-play-po-v0.145.md・作業ブランチ `claude/poison-mist-play-po`）。集合 `CS-KYUURA-PLAY-PO@1`（開発用・halts_at_undecided）。
- 作業の承認（2 章）と、具体的な続行仕様の採用（この章）は別の記録です。2 章の「仕様: not_approved」と 1〜12 章は提案の時点の記録で、書き換えていません。

| 選択肢 | 採用 |
|---|---|
| OC-PO-1 | 推奨のとおり（性質 → ［ポイズンミスト］→ 鋼エネルギー） |
| OC-PO-2 | 推奨のとおり（時点でどく状態のすべてのポケモン） |
| OC-PO-3 | 推奨のとおり（場をはなれたら終わる。#source-left だけ） |
| OC-PO-4 | 推奨のとおり（#power-lost は扱わず、続行側でも止める） |
| OC-PO-5 | 推奨のとおり（新しい ID CS-KYUURA-PLAY-PO@1。S2a の 5 規約を引き継ぎ、PO の 3 規約を加える） |
| OC-PO-6 | 推奨のとおり（convention_applied を残す） |

仕様案からの差・実装で具体化したこと:

- 規約を当てた記録の単位: どくのダメージを受けるポケモンごと、量を決めた規約ごとに 1 つ（PC-POISON-MIST-SOURCE-LEFT → PC-POISON-MIST-TARGETS → PC-POISON-AMOUNT-ORDER の順）を、そのポケモンの poison_damage の直前に書く。規約は厳密側の判断で止まるときだけ、その順に 1 つずつ加えて求め直し、量が決まったところでやめる。加えた規約のうち、それを除くと結果（止まる・量）が変わるものだけを記録する（最後に加えた規約はいつも入る）。
- PC-POISON-AMOUNT-ORDER: 性質の 2 つ（特殊などくの量とかける数）のあいだの順番は決めない（今の写しでは同時に持たない。持てばエンジンの不具合として RuntimeError）。かける数は鋼エネルギーより先。
- PC-POISON-MIST-SOURCE-LEFT: 場をはなれたかは、記録の発生源の場の番号のポケモンがポケモンチェックの時点で場にいないかで判断する（新しい状態の項目は加えていない）。記録ごとに判断し、発生源が 2 匹以上でもそれぞれの記録を分けて扱う（2 つ以上の記録は足さない v0.119 のまま）。
- ログの poison_mists は、PC-POISON-MIST-TARGETS を当てたときだけ使う前からどく状態のポケモンの記録をふくむ（ほかは今のまま）。
