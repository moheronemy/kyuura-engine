# 未決場面を共通規約で扱うための設計案と優先順位

この文書は調査・設計・文書化の記録です。**規約の採用、エンジンの動作の変更、モードの実装はしていません。** ここに書く共通規約（`PC-*`）はどれも**案**で、利用者の承認を
受けていません（設計案の JSON の `status` は `proposal` だけ。`--check` が確かめる）。エンジン・既存のテスト・カードデータ・固定デッキ・過去の参照データ・kyuura・利用者の `.claude/` は
変えていません。

- 構造化した設計案: [play-policy-family-plan.json](play-policy-family-plan.json)（`scripts/build_play_policy_family_plan.py --write` で作り、`--check` で停止の方針の台帳と突き合わせる）。
  この文書の表のうち「生成」の印のあるものは、同じスクリプトが JSON から書く（手で直さない）
- 場面（事例）の唯一の元: [stop-policy-classification.json](stop-policy-classification.json) の `entries`（ID で引くだけ。台帳の記録・集計は書き換えていない）
- モードと規約集合の設計: [ruleset-mode-design.md](ruleset-mode-design.md)・判断事項: [ruleset-mode-decisions.md](ruleset-mode-decisions.md)・[stop-policy-decisions.md](stop-policy-decisions.md)

## 1. 基点と調査範囲

| 項目 | 値 |
|---|---|
| 基点 | `8164194ca289c5f7f332c7f16d7f700a81a37215`（v0.141 の最後のコミット。`origin/claude/prize-order-v0140-cleanup` と同じ。版 0.141.0） |
| `origin/main` | `816bcffb86edeb3ea713ee08818a070e036fe0a8`（PR #35 の v0.140 のマージ。木は `c68b3cd` と同じ）。v0.141（`834cdcb`〜`8164194`）は main に取り込まれていない |
| 基点を選んだ理由 | v0.141 で直した拒否の文（旧版の状態と矛盾した状態の書き分け）と legacy 参照の確かめを含めるため。v0.141 の変更は拒否の文・テスト・文書だけで、停止コードの集合・止め方は main と同じ |
| 作業ブランチ | `claude/play-policy-family-plan`（基点から） |
| 未コミットの変更 | 利用者の `.claude/`（追跡していない）だけ。変えていない |
| kyuura | `C:/dev/kyuura` は `b9e7cff`（読んだだけ）。エンジンが参照する固定コミットは `71d1728` |

調査した範囲:

- **台帳**: 停止の方針の台帳の現在有効な項目（`status` が active・unverified。事例のあるコードは事例）を、すべて場面として対応付けた。台帳の集計は分類の時点（v0.136）の値のまま
  書き換えず、この文書の件数は今の台帳から数え直した（古い集計を転記していない）。
- **現行のコード**: 停止の文（`UnsupportedError` の引数・`*_REASON` の定数）を AST で集め（`effects.py` などの 303 コード。残りは理由の定数・研究の対応表から）、対戦全体を止める経路
  （準備・ポケモンチェック・番の終わり・途中停止・決定の答えがない HALTED）は箇所を読んで確かめた（4 章）。
- **研究の記録**: 台帳の `research`（固定研究基準 `71d1728` の対応表とエンジンの裁定の文書）を引いた。公式資料の再調査・kyuura の後続の記録の照合はしていない。
- **発生の記録**: 今の木で、旧バッチの道具の全 108 バッチと延長戦の道具を流し直した（6 章。版・組・方策・seed・分母を書く）。
- **比較プローブ**: キョウの忍者ジムの使う前の確かめで、新しい情報漏れを 1 件確かめた（7 章。修正していない）。

## 2. 分類の軸

### 2.1 区分（利用者の依頼の A〜E）

台帳の `classification`（棚卸しの A〜E。A=機能不足・B=技術的制限・C=未裁定・D=独自規約・E=その他）とは**別の軸**です。同じ文字でも意味が違います（JSON の `plan_class` と
`ledger_classification` を別に持つ）。

| 区分 | 意味 |
|---|---|
| A | プレイ用の規約で続けられる候補の、研究上の未決場面。研究の停止コード（固定研究基準の対応表）だけ。名前が UNRESOLVED でも、汎用の `UNRESOLVED_RULING` は A にしない（E・問いは unknown） |
| B | エンジンの機能不足（継続の状態・写したワザの実装・登録・データ・途中停止の再開） |
| C | 技術的な制限（探索・組合せ・表現の上限） |
| D | 情報漏れ・内部エラー・状態の整合性・止めすぎなど、両モードで直す共通の不具合（候補・未確認を含む） |
| E | 採用済みの規約・対象外・テストだけのコード・コードのない問い・不正入力・状態の互換の拒否など |

A の場面でも、続けるのに実装・秘密への非依存の確かめ・不具合の修正が要るものは、続けられ方（2.2 節）で分けます。台帳の対応群（3 = 実装が要る・5 = 保護が要る）は、規約案の
続けられ方の下限として当てました（規約案の側で「規約だけで足りる」と書いても、台帳が実装を要るとしていれば `needs_implementation` にする）。

### 2.2 続けられ方（規約案の対象の場面ごと）

| 値 | 意味 |
|---|---|
| `full` | 規約だけで続けられる。現行コードの分岐を読み、規約が答えればその停止の箇所にほかの停止がないことを確かめた |
| `question_resolved_other_stops_possible` | 規約は場面の問いに答えるが、その後の処理で既存のほかの停止に当たりうる（コードで確かめた） |
| `partial` | 場面に問いが複数あり、規約が答えるのは一部 |
| `needs_implementation` | 規約に加えて、エンジンの実装が要る |
| `needs_secret_review` | 規約に加えて、秘密への非依存（対の比べ）の確かめ直しが要る |
| `blocked_by_defect` | 同じ場面に未修正・未確認の共通の不具合がある。不具合を直す前に規約を採らない |
| `unverified` | 停止の文・裁定の記録の行から当てたもので、規約で続けられるかはコードで確かめていない |

`unverified` を「続けられる」「共通化できる」とは数えません（5 章の集計で別に数える）。

### 2.3 不足の種類（利用者の依頼の区別）

「対象がない」に見える場面を、次の種類に分けて別の規約案にしました（同じ言葉でも 1 つの原則で安全に扱えないため）。

| 種類 | 規約案 | 分けた理由 |
|---|---|---|
| 対象が最初からない（使う宣言の時点。公開の領域・本人の手札） | `PC-USE-WITHOUT-TARGET` | 宣言の前に公開の情報で決まる。「使えない」なら今の挙動と同じ |
| 効果の途中で対象・発生源がいなくなる | `PC-TARGET-LOST-MID-EFFECT` | 処理の途中の状態（継続）が要る。最初からない場面の答えを流用できない |
| コインで決まった必要な枚数が不足する | `PC-COIN-COUNT-SHORT` | 乱数のあとに分かるので「使えない」にできない（今は途中停止） |
| 説明の決まった枚数が、使う時点の公開の枚数より多い | `PC-STATED-COUNT-SHORT` | 宣言の前に公開の枚数で分かる |
| コストを払えない | `PC-RETREAT-COST-PAYMENT`（にげる）。特殊能力の手札のトラッシュ（PW2）は個別 | コストの払い方は手順ごとに違う。共通の規約にできたのはにげるだけ |
| 非公開の場所（山札）を探して見つからない | `PC-HIDDEN-SEARCH-EMPTY` | 受け付けが秘密に依存しないことが先（v0.137・v0.138 の下限）。公開の領域の答えを流用しない |
| 対象はあるが、使っても・選んでも何も起こらない | `PC-USE-WITHOUT-EFFECT`・`PC-CHOOSE-TARGET-WITHOUT-EFFECT` | 使う段階と選ぶ段階で、問い・止め方が違う |

既存の利用者指定は、指定の対象のまま扱います。ひかるバンギラス neo4-082 の 2 つのワザ（「足りなければあるだけ」）は、`PC-COIN-COUNT-SHORT`・`PC-STATED-COUNT-SHORT` の根拠にも
対象にもしていません（除外に明記）。サイドを取る順番の利用者指定（USER-PRIZE-ORDER-*）は「同じきぜつの処理」の場面だけで、ポケモンチェックの両方のきぜつへ自動で広げていません
（`PC-CHECK-DOUBLE-KNOCKOUT` の代替案として、利用者が決める）。

## 3. 現行の分類と集計（今の台帳から数え直した値）

<!-- generated:plan-counts begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 対象 | 件数 |
|---|---:|
| 場面（台帳の現在有効な項目。事例のあるコードは事例） | 400 |
| うち停止コードの場面 | 366 |
| 停止コード（重複を除く） | 357 |
| 区分 A（研究上の未決場面） | 325 |
| 区分 B（機能不足） | 33 |
| 区分 C（技術的な制限） | 14 |
| 区分 D（共通の不具合） | 9 |
| 区分 E（そのほか） | 19 |
| A のうち規約案の対象 | 170 |
| A のうち個別（共通化しない） | 155 |
| 規約案 | 27 |
| 規約案の対象の場面（重複を含む） | 170 |
| 規約案の対象の場面（重複を除く） | 170 |
| 関連する停止コード（重複を含む） | 166 |
| 関連する停止コード（重複を除く） | 163 |
| 規約だけで続けられる場面（full） | 2 |
| 一部だけ扱える場面 | 5 |
| 追加の実装・秘密の確かめ・不具合の修正が要る場面 | 37 |
| 続けられるか未確認の場面（unverified） | 126 |
| 対戦全体を止める場面（静的な止め方と、経路の一覧の場面） | 28 |
| うち静的な Halt・途中停止の定数で止める | 16 |
| うち動的な経路（4 章の一覧）でだけ止める（ほかの場面では拒否） | 12 |
| 対戦全体を止める場面のうち規約案の対象 | 15 |
| この調査で見つけた不具合 | 1 |
| 内部ガード（場面に数えない。D） | 604 |
<!-- generated:plan-counts end -->

A 以外の場面の内訳（理由ごと）:

<!-- generated:plan-classes begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 区分 | 理由 | 場面 |
|---|---|---:|
| B | 決定・反応の継続の状態がない（エンジンの未対応） | 15 |
| B | 未登録・未対応のカード・ワザ・操作（登録の不足。推測で進めない） | 6 |
| B | 写したワザ・特殊能力の処理の実装がない | 5 |
| B | データ・記録の不足（図鑑番号・身長・進化元・旧状態の記録・デッキリスト） | 5 |
| B | 途中停止の再開の操作がない（エンジンの未対応） | 1 |
| B | 参照データの不足（図鑑番号のない 225 枚） | 1 |
| C | 技術的な上限・探索の fail-open | 7 |
| C | 探索・組合せの上限（未探索の枝を安全とみなさない） | 6 |
| C | 表現の上限 | 1 |
| D | 情報漏れ（未修正） | 2 |
| D | 先読みの止めすぎ（受け付けてよい操作を拒否する不具合の候補） | 2 |
| D | 代わりの処理の安全性の見直し（未確認） | 2 |
| D | 情報漏れの候補（未確認） | 1 |
| D | 代替回答探索の fail-open（未探索を受け付ける側に倒す。安全境界 SB-NO-FAIL-OPEN-SEARCH の候補） | 1 |
| D | この調査で見つけた情報漏れ（未修正。台帳には未登録） | 1 |
| E | テスト・道具だけのコード（エンジンでは投げない） | 8 |
| E | コードのない研究の問い。エンジンが止める場面かは確かめていない（到達可能性 unknown） | 5 |
| E | 汎用の UNRESOLVED_RULING。どの問いか分からない（名前が UNRESOLVED でも A にしない。到達可能性・問いは unknown） | 1 |
| E | デッキの検査（不正入力。SB-INPUT-VALIDATION） | 1 |
| E | この版が扱えない状態の規約集合（状態の互換・登録との不一致の拒否。v0.142。規約の対象ではない） | 1 |
| E | この版が知らない再開先の決定を待つ状態（状態の互換の拒否。v0.141 で文を直した。規約の対象ではない） | 1 |
| E | 対象外（特別なルール） | 1 |
| E | 研究の基準の照合（記録の作業） | 1 |
<!-- generated:plan-classes end -->

採用済みの規約（台帳の `conventions`）は場面に数えず、JSON の `adopted_conventions` に ID・区分・方針の状態だけを写しました（E。利用者指定は両モードの基礎集合。ほかは未決のまま）。
内部ガード（`RuntimeError` など）は場面に数えず、個数だけを持ちます（D。合法な操作の列で起きたら不具合として扱う。台帳 10 章の SB-ENGINE-BUG-GUARDS）。

## 4. 対戦全体を止める論点群

### 4.1 経路（現行コードで確かめた）

止め方を、未決の裁定による停止・途中停止・技術的な停止・道具の打ち切りに分けました。静的な `Halt` の定数に加えて、ほかの停止が HALTED に変わる動的な経路も箇所で確かめました
（どのコードが動的な経路を通るかの全件は特定していない。8 章）。

<!-- generated:plan-whole-game begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 経路 | 種類 | 止め方 | 箇所 | 場面 | 規約案 | 続けるのに要るもの |
|---|---|---|---|---|---|---|
| `WG-SETUP-MULLIGAN` | unresolved_ruling | setup_halt | kyuura_engine/engine.py:513〜526（_deal_opening_hands） | 2 | PC-SETUP-MULLIGAN-COUNT | 規約だけで続けられる（補償の数を決めれば、既存の DrawMulliganCards で引く） |
| `WG-SETUP-PLAY-AS-POKEMON` | unresolved_ruling | setup_halt | kyuura_engine/engine.py:491〜500 | 2 | PC-SETUP-PLAY-AS-POKEMON | 「切り直す」なら規約だけ。「出せる」なら準備で置く処理の実装が要る。どちらでも、その後の切り直しで WG-SETUP-MULLIGAN に当たりうる |
| `WG-CHECK-SLEEP-ORDER` | unresolved_ruling | pokemon_check_halt | kyuura_engine/procedures.py:946〜961 | 1 | PC-CHECK-SIDE-ORDER | 規約で順番が決まる。そのあと回復したときの止め方（WG-CHECK-RECOVERY）に当たりうる |
| `WG-CHECK-CHAR-ORDER` | unresolved_ruling | pokemon_check_halt | kyuura_engine/procedures.py:374〜381 | 1 | PC-CHECK-SIDE-ORDER | 規約で順番が決まる。コインの前の確かめ・上限（WG-CHECK-CHAR-LIMIT）が残る |
| `WG-CHECK-CHAR-LIMIT` | technical_limit | pokemon_check_halt | kyuura_engine/procedures.py:382〜385 | 1 | — | 規約では続けられない（計算の改善が要る。C） |
| `WG-CHECK-PLAN` | unresolved_ruling | pokemon_check_halt | kyuura_engine/procedures.py:267〜330（_pokemon_check_plan） | 11 | PC-CHECK-SIDE-ORDER・PC-NON-ATTACK-DAMAGE-MODIFIERS・PC-CHECK-KO-POINT・PC-CHECK-DOUBLE-KNOCKOUT・PC-LASTING-SOURCE-CHANGE | コードごと。SC1・AL1・AL3・PO1・PO2 はカード固有（個別）。きのみの上限は C |
| `WG-CHECK-SCRAM` | unresolved_ruling | pokemon_check_halt | kyuura_engine/resolution/flow.py:1290〜1300 | 1 | — | カード固有の時点の読み方（個別） |
| `WG-CHECK-RECOVERY` | unresolved_ruling | pokemon_check_halt | kyuura_engine/procedures.py:966〜981・1009〜1015（_recovery_stop → effects.state_stop_after） | 4 | PC-NON-DAMAGE-HP-KNOCKOUT | MH1 は規約と判定の時点の実装。姿の問いはカード固有。コードの全件の列挙はしていない（form_problems が返すコードは静的に一部だけ確かめた） |
| `WG-TURN-END-SUPPRESSION` | unresolved_ruling | turn_end_halt | kyuura_engine/procedures.py:80〜99（expire_at_turn_end → state_stop_after） | 3 | PC-NON-DAMAGE-HP-KNOCKOUT | WG-CHECK-RECOVERY と同じ |
| `WG-TURN-END-MIRACLE` | unresolved_ruling | turn_end_halt | kyuura_engine/procedures.py:100〜105（miracle_turn_end_problem） | 1 | — | カード固有（個別） |
| `WG-DEFERRED-SHORTAGE` | unresolved_ruling | deferred_interruption | kyuura_engine/engine.py:892〜895（DeferredShortage → _interrupted） | 2 | PC-COIN-COUNT-SHORT | 規約を採れば、途中停止にせず最初から規約で処理する（すでに途中停止した状態の再開は別の判断 DEC-DEFERRED-RESUME） |
| `WG-DECISION-NO-ANSWER` | dynamic_conversion | decision_halt | kyuura_engine/engine.py:579〜588・896〜903・943〜953（_decision_has_unstopped_answer） | 3 | PC-FACE-UP-DECK・PC-NON-DAMAGE-HP-KNOCKOUT | 当たったコードの規約・実装による。どのコードがここを通るかの全件は静的に特定していない（台帳 14 章の限界のまま） |
| `WG-OBSERVED-UNIDENTIFIED` | dynamic_conversion | observed_halt | 経路は特定していない（道具の対戦で HALTED を観測。tools/existing_effect_games.py の v0.49 の組 A49-D49・seed 2。6 章） | 1 | — | 規約では続けられない（B。写した特殊能力の実装が要る） |
| `WG-TOOL-LIMITS` | tool_cutoff | tool_step_limit | tools/existing_effect_games.py の --max-steps・予期しない拒否（unexpected_rejection）・サドン・デスに移った局（延長戦を進めない）。tools/sudden_death_games.py の segment_limit | 0 | — | 規約の対象ではない（道具の設定）。集計では HALTED と分けて数える |
<!-- generated:plan-whole-game end -->

### 4.2 切り直しの補償（`UNRESOLVED_MULLIGAN_COMPENSATION`）

- **今の止まる条件**（`engine._deal_opening_hands`）: 7 枚を配り、たねポケモン（ベイビィを含む）のないプレイヤーだけが切り直す。回ごとに、切り直したプレイヤーの組を
  `mulligan_rounds` に記録する。切り直しの回は「両方の回」（2 人とも）と「片方だけの回」（1 人）で、両方の回のあとに片方だけの回が続く形だけが起こる（片方だけの回で切り直すのは、
  同じプレイヤーだけ。たねポケモンの来たプレイヤーはもう切り直さない）。**両方の回と片方だけの回が両方あるときだけ**、準備を HALTED にする。
- **未決の点**: 補償の**回数**だけです。補償 1 回の枚数（0〜2 枚）と時点（サイドを置いたあと・ジャンケンの前）は、通常の補償の実装上の読み方（rules-2000-02-14.md の記録）をそのまま
  使えます。回数が違うときに時点を変える根拠はありません。
- **通常の片側の切り直しとの関係**: 片方だけの回しかないときは、今のまま 1 回ごとに補償 1 回（`DrawMulliganCards`）。両方の回しかないときは、今のまま、どちらも引かない。
- **両側の切り直しのあとに片方だけが追加で切り直す場合**: 規約案 `PC-SETUP-MULLIGAN-COUNT`（推奨は回ごとに数える: 片方だけの回 1 回につき補償 1 回。両方の回は数えない）。
  数は両者の切り直しの回数の差と同じです。代替案（両方の回が一度でもあれば補償なし）は JSON に理由とともに書きました。
- **サドン・デスの準備への適用**: 延長戦の区間の準備（`engine._prepare_segment`）は同じ関数を呼ぶので、同じ規約が同じ条件で当たります（事例 `#sudden-death-segment`）。区間ごとの
  実装は要りません。区間の記録の `mulligan_rounds` は reset（v0.134 の `SEGMENT_FIELD_POLICY`）。
- **化石・人形の初手との依存**: たねポケモンのない手札に、なにかの化石・ピッピ人形があると、切り直す**前に** `UNRESOLVED_PLAY_AS_POKEMON_SETUP` で止めます（回ごとに確かめる）。
  `PC-SETUP-PLAY-AS-POKEMON` で「切り直す」を採ると、切り直しの回が増え、その結果として `PC-SETUP-MULLIGAN-COUNT` の場面に当たりうる（逆に補償の規約だけを採っても、化石・人形の
  手札では止まる）。2 つは別の問いで、別に採れます。
- **続けられ方**: 規約だけで続けられる（`full`）。補償の数を決めれば、既存の `DrawMulliganCards` と不変条件で引けます。

### 4.3 ポケモンチェックの停止

ポケモンチェックはどちらの番でもありません（p.323）。今の止め方は、ダメージ・コインの前に複製の上で確かめて止めるものです（コマンドを拒否しても、どの操作でも番は終わるので、
対戦を止める）。

- **両側の特殊状態・同時の処理の順番**（ねむりのコイン・くろこげマーカーのコイン）: `PC-CHECK-SIDE-ORDER`。推奨は「番を終えたプレイヤーの場から」（ログの順と同じ）。規約で順番が
  決まっても、ねむりは回復したときの止め方（`_recovery_stop`: MH1・TF1・TF2・DG1）、くろこげマーカーはコインの前の確かめ（BY1・PK1・SC1・両方のきぜつ）と上限
  （`UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`。C）が残ります。
- **両方のきぜつ**: 問いが 3 つ（同時か・バトル場に出す順番・サイドを取る順番を決める人）。`PC-CHECK-DOUBLE-KNOCKOUT` は (1) を同時のきぜつとし、(2)(3) を `PC-CHECK-SIDE-ORDER` に
  そろえる案です。v0.140 の決定（prize_first）は、ポケモンチェックの続きでは出さない作りなので、続けるには実装が要ります（`partial`）。
- **途中のきぜつ**（PK1）: `PC-CHECK-KO-POINT`（2 のあとに 1 回だけ判定）。
- **どくのダメージと受けるダメージを変える特殊能力**（KA1）: `PC-NON-ATTACK-DAMAGE-MODIFIERS`（ワザ以外のダメージには当てはめない）。こんらんの自分へのダメージ（道具の対戦で拒否が多い）と
  同じ規約で扱える案です。
- **カード固有の停止**（共通化しない）: ［ずらかる］の時点（SC1・SC2）・アンノーンのロックの離脱（AL1・AL3）・どくの量の合わせ方（PO1）・［ポイズンミスト］（PO2・PO3）・
  きのみの順番（BY1。効果の種類の順番を含む）。
- **道具の対戦で多く止めたもの**（6 章）: 両方のねむり・化石と人形の初手・切り直しの補償に続いて、［ポイズンミスト］の PO2・PO3 がポケモンチェックの HALTED を起こしました。
  PO3 は `PC-LASTING-SOURCE-CHANGE` の対象で、使ったポケモンが場にいない場合だけを扱います（`partial`）。PO2 は個別です。共通の規約案だけでは、ポケモンチェックの停止はなくなりません。
  ［ポイズンミスト］の 2 つの問いは、1 枚のカードの判断として先に決める候補です（9 章）。

### 4.4 途中停止（DU1・TW1）

コインのあとに、コインで決まった枚数が足りないと分かる場面です。今は途中停止（`Phase.HALTED` と `Halt.interruption`。再開の操作はない）。`PC-COIN-COUNT-SHORT`（あるだけ処理する）を
採れば、途中停止にせず最初から規約で処理します。すでに途中停止した保存状態の再開は別の判断（DEC-DEFERRED-RESUME）で、この規約は再開の操作を作りません。

### 4.5 決定の答えがない HALTED（動的）

決定（バトル場に出す・サイドを取る・決定への答え）とジャンケンの報告で、どの答えでも受け付けられない状態になるなら、答えのない決定を残さずに HALTED にします。当たるコードは、
決められない姿・MH1・SC2・おもての山札（FU3 など）・うらのカードの項目（FD1）です。続けられるかは、当たったコードの規約・実装によります。

### 4.6 規約が決まれば続けられるもの・追加の実装がなければ続けられないもの

- **規約だけで続けられる見込み**: 切り直しの補償（確かめた）。化石・人形の初手（推奨案なら規約だけ。その後に補償の場面に当たりうる）。両側のねむり・くろこげマーカー（順番は規約だけで
  決まり、その後に既存の停止が残る）。途中のきぜつの時点・途中停止の 2 つ（コードの後続は確かめていない）。
- **追加の実装が要る**: ポケモンチェックの両方のきぜつ（続きの並び）・ダメージ以外の HP 低下のきぜつ（判定の窓）・ワザ以外のダメージの量（問い合わせの部品）。
- **規約では続けられない**: くろこげマーカー・きのみの上限（C）。道具の打ち切り（エンジンの停止ではない）。

## 5. 共通規約案とカバー範囲

### 5.1 一覧（生成）

<!-- generated:plan-candidates begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 規約案 | 名前 | 群 | 全体停止 | 場面 | コード | 続けられ方（場面の数） | 推奨（案） | 判断事項 |
|---|---|---|:---:|---:|---:|---|---|---|
| `PC-SETUP-MULLIGAN-COUNT` | 回数の違う切り直しの補償の数え方 | setup | ○ | 2 | 1 | full 2 | 回ごとに数える（片方だけの回 1 回につき補償 1 回） | DEC-MULLIGAN-COMPENSATION |
| `PC-SETUP-PLAY-AS-POKEMON` | 準備の手札のなにかの化石・ピッピ人形 | setup | ○ | 2 | 1 | question_resolved_other_stops_possible 2 | 数えない（切り直す） | DEC-PLAY-AS-POKEMON |
| `PC-CHECK-SIDE-ORDER` | ポケモンチェックで両方のプレイヤーが同じ処理をする順番 | pokemon_check | ○ | 3 | 3 | question_resolved_other_stops_possible 2・unverified 1 | 番を終えたプレイヤーから | DEC-SLEEP-COIN-ORDER・DEC-ORDER-RULE |
| `PC-CHECK-DOUBLE-KNOCKOUT` | ポケモンチェックの両方のきぜつ | pokemon_check | ○ | 1 | 1 | partial 1 | (1) 同時のきぜつとして扱う。(2)(3) は PC-CHECK-SIDE-ORDER にしたがう | DEC-KNOCKOUT-READINGS・DEC-ORDER-RULE |
| `PC-CHECK-KO-POINT` | ポケモンチェックの途中のきぜつの判定の時点 | pokemon_check | ○ | 1 | 1 | unverified 1 | 2 のあとに 1 回だけ判定 | DEC-KNOCKOUT-READINGS |
| `PC-COIN-COUNT-SHORT` | コインで決まった枚数が足りないとき（途中停止の 2 つ） | count | ○ | 2 | 2 | unverified 2 | あるだけ処理する | DEC-STATED-COUNT-SHORT・DEC-DEFERRED-RESUME |
| `PC-STATED-COUNT-SHORT` | 説明の決まった枚数が公開の枚数より多いとき | count |  | 9 | 9 | unverified 9 | 使える（あるだけ処理する） | DEC-STATED-COUNT-SHORT |
| `PC-USE-WITHOUT-TARGET` | 選ぶ対象が最初からないときに使えるか | target |  | 38 | 38 | blocked_by_defect 1・unverified 37 | 使えない | DEC-USE-WITHOUT-EFFECT |
| `PC-HIDDEN-SEARCH-EMPTY` | 山札を探す効果で、目的のカードが見つからないとき | target |  | 4 | 4 | blocked_by_defect 1・needs_secret_review 3 | 使える（見つからなければ何も選ばない） | DEC-USE-WITHOUT-EFFECT・DEC-INFO-LEAK-FIXES |
| `PC-USE-WITHOUT-EFFECT` | 使っても何も起こらないときに使えるか | target |  | 7 | 7 | unverified 7 | 使えない | DEC-USE-WITHOUT-EFFECT |
| `PC-CHOOSE-TARGET-WITHOUT-EFFECT` | 選んでも何も起こらないポケモンを選べるか | target |  | 5 | 5 | unverified 5 | 選べない | DEC-USE-WITHOUT-EFFECT |
| `PC-UP-TO-ZERO` | 「最大N」「好きなだけ」で 0 を選べるか | count |  | 13 | 13 | blocked_by_defect 1・unverified 12 | 0 を選べる | DEC-UP-TO-ZERO |
| `PC-NON-ATTACK-DAMAGE-MODIFIERS` | ワザ以外のダメージに、ダメージを変える効果を当てはめるか | damage | ○ | 10 | 10 | unverified 10 | 当てはめない | DEC-DAMAGE-READINGS |
| `PC-UNSTATED-WEAKNESS-RESISTANCE` | 「弱点・抵抗力に関係なく」と書かれていないワザ以外・控えへのダメージの弱点・抵抗力 | damage |  | 2 | 2 | unverified 2 | 計算しない | DEC-DAMAGE-READINGS |
| `PC-SPECIAL-ENERGY-CARD-WORDING` | 特殊エネルギーカードは「X エネルギーカード」か | energy |  | 9 | 9 | unverified 9 | 基本 X エネルギーカードだけ | DEC-ENERGY-READINGS |
| `PC-RETREAT-COST-PAYMENT` | にげるのコストの払い方 | energy |  | 2 | 2 | unverified 2 | 最小の組で払い、余りは捨てる。0 を下回ったら 0 | DEC-ENERGY-READINGS |
| `PC-NULLIFIED-ELEMENT-COIN` | 効果がはたらかない要素のコインを投げるか | coin |  | 5 | 5 | unverified 5 | 投げる | DEC-NULLIFIED-COINS |
| `PC-ORDER-ATTACK-PRECHECK` | ワザのダメージの前の複数のコインの順番 | order |  | 7 | 7 | unverified 7 | 番のプレイヤーが選ぶ | DEC-ORDER-RULE |
| `PC-ORDER-OVERLAP` | 同じ時点にはたらく複数の効果の当てはめの順番 | order |  | 10 | 10 | unverified 10 | 番のプレイヤーが選ぶ | DEC-ORDER-RULE |
| `PC-SUPPRESSION-LATER-POKEMON` | 特殊能力を消す効果は、あとから場に出たポケモンにも及ぶか | power |  | 3 | 3 | unverified 3 | 及ぶ | DEC-SUPPRESSION-READINGS |
| `PC-NON-DAMAGE-HP-KNOCKOUT` | ダメージ以外で HP がのっているダメージ以下になったポケモン | knockout | ○ | 3 | 3 | blocked_by_defect 1・needs_implementation 1・unverified 1 | 原因のコマンドの処理の終わりに判定 | DEC-KNOCKOUT-READINGS |
| `PC-REACTION-DOUBLE-KNOCKOUT` | ワザのダメージと反応のダメージによる両方のきぜつ | knockout |  | 3 | 3 | unverified 3 | 同時のきぜつ | DEC-KNOCKOUT-READINGS |
| `PC-TARGET-LOST-MID-EFFECT` | 効果の途中で対象・発生源がいなくなったとき | target |  | 4 | 4 | needs_implementation 4 | そのポケモンに関する残りを行わない | DEC-REACTION-READINGS・DEC-COPY-SCOPE |
| `PC-LASTING-SOURCE-CHANGE` | 持続する効果の発生源が進化・退化・場をはなれたとき | lasting | ○ | 6 | 6 | needs_implementation 6 | 場をはなれたら終わる・進化・退化では続く | DEC-LASTING-READINGS |
| `PC-ONCE-PER-TURN-IDENTITY` | 「番に 1 回」「その番に〜した」の記録は、入れかわり・もどりで続くか | lasting |  | 5 | 5 | blocked_by_defect 1・needs_implementation 4 | 続く（使い直せない） | DEC-LASTING-READINGS |
| `PC-COPIED-ATTACK-AS-OWN` | 写したワザは、写したポケモンのワザとして説明のすべてを処理するか | copy |  | 7 | 7 | needs_implementation 7 | 写したポケモンのワザとして説明のすべてを処理 | DEC-COPY-SCOPE |
| `PC-FACE-UP-DECK` | フラッシュでおもてになった山札のカード | hidden | ○ | 7 | 5 | needs_secret_review 7 | おもてのまま・移る時点の公開だけを残す | DEC-FACE-UP-DECK |
<!-- generated:plan-candidates end -->

1 つの場面に当たる規約案は 1 つだけです（`--check` が確かめる。暗黙の優先順位を作らない）。事例を分けたコード（ST1・UPZ2・FC1 など）は、事例ごとに別の規約案に当てたので、
コードの数は重複を含む数と除いた数が違います（3 章）。

### 5.2 各規約案の内容（生成）

<!-- generated:plan-candidate-details begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
#### PC-SETUP-MULLIGAN-COUNT: 回数の違う切り直しの補償の数え方

- **問い**: 両方のプレイヤーが同時に切り直した回のあとに、片方だけがさらに切り直したとき、相手は何回ぶんの補償（1 回ごとに最大 2 枚）を引けるか
- **規約の文（案）**: 準備の切り直しを回ごとに数える。両方のプレイヤーが同時に切り直した回は、どちらにも補償を与えない。片方のプレイヤーだけが切り直した回は、1 回ごとに、もう一方のプレイヤーに補償 1 回（山札から 0〜2 枚。DrawMulliganCards 1 回）を与える。引く時点は、回数が同じでない場合も今の補償と同じ（サイドを置いたあと、ジャンケンの前）
- **適用条件**: engine._deal_opening_hands の切り直しの回の列（mulligan_rounds）に、両方の回と片方だけの回が両方ある（今 UNRESOLVED_MULLIGAN_COMPENSATION で準備を HALTED にする条件そのもの）
- **対象の場面（続けられ方）**: `UNRESOLVED_MULLIGAN_COMPENSATION#initial-setup`（full）、`UNRESOLVED_MULLIGAN_COMPENSATION#sudden-death-segment`（full）
- **除外・対象外の隣の場面**: 片方だけの回しかない切り直し（今の補償のまま）／両方の回しかない切り直し（今のまま、どちらも引かない）／なにかの化石・ピッピ人形がある手札（PC-SETUP-PLAY-AS-POKEMON。切り直しの前に止める）
- **依存・関係・競合**: 依存 なし／関係 PC-SETUP-PLAY-AS-POKEMON／競合 なし
- **厳密モードとの差**: 厳密は今のまま準備で HALTED。プレイ用は止めずに、片方だけの回の数（= 両者の切り直しの回数の差）ぶんの補償を与える
- **影響**: 公開の情報 変えない（切り直しの手札の公開・補償の枚数の選択は今のまま）／乱数 補償で引くのは山札の上から（乱数を新しく使わない）。止めないので、その後の対戦の乱数を使う／コスト なし／処理の順番 補償の時点は今と同じ
- **共通処理で実装できる範囲**: engine._deal_opening_hands の HALTED の分岐を、規約の照会（規約集合に PC-SETUP-MULLIGAN-COUNT があるか）で補償の数に置きかえる。同じ関数を延長戦の区間も使う（engine._prepare_segment）ので、区間ごとの実装は要らない
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 両方の回 1・片方だけの回 1・2 の盤面で、補償の回数・DrawMulliganCards の受け付け・ログ・観測／片方だけの回だけ・両方の回だけの盤面が今と同じ（厳密・プレイ用とも）／延長戦の区間でも同じ／厳密の集合では今と同じ HALTED
- **推奨（案）**: 回ごとに数える（片方だけの回 1 回につき補償 1 回）（p.308 の 2 つの文（片方の切り直しごとの補償・両方のときはどちらも引かない）を、回ごとにそのまま当てはめる読み方で、席・先攻後攻によらない。数は両者の切り直しの回数の差と同じ）
- **代替案**: 両方の回が一度でもあれば、どちらも引かない（「両方とも」の文を準備全体に当てはめる読み方。補償を受けられない側の不利が大きい）／相手の切り直しの総数ぶん引ける（両方の回も数える）（「両方とも…引かない」の文と合わない（採らない案として記録））
- **根拠**: docs/rules-2000-02-14.md の p.308 の表（切り直し・補償・両方とも切り直し）と未解決の行／engine.py:513〜528（halt の条件と補償の数え方）／kyuura docs/engine-readiness.md 4 章（読んだだけ）。研究の記録: 裁定 —、kyuura の論点 —
- **未確認**: 公式資料に回数が違う場合の記述がないことの再確認（研究上は未解決のまま）
- **判断事項**: DEC-MULLIGAN-COMPENSATION（状態 proposal）

#### PC-SETUP-PLAY-AS-POKEMON: 準備の手札のなにかの化石・ピッピ人形

- **問い**: たねポケモンがなく、なにかの化石・ピッピ人形（たねポケモンとして場に出せるトレーナー）がある最初の手札で、切り直すのか、それを最初のポケモンとして出せるのか
- **規約の文（案）**: 準備の切り直しの判定では、たねポケモンとして場に出せるトレーナー（なにかの化石・ピッピ人形）を、たねポケモンカードとして数えない。たねポケモンカード・ベイビィポケモンカードがなければ、今の切り直しと同じく切り直す
- **適用条件**: engine._deal_opening_hands で、たねポケモンのない手札に play_as_pokemon_in_hand のカードがある（今 UNRESOLVED_PLAY_AS_POKEMON_SETUP で HALTED にする条件）
- **対象の場面（続けられ方）**: `UNRESOLVED_PLAY_AS_POKEMON_SETUP#initial-setup`（question_resolved_other_stops_possible）、`UNRESOLVED_PLAY_AS_POKEMON_SETUP#sudden-death-segment`（question_resolved_other_stops_possible）
- **除外・対象外の隣の場面**: 準備でない場面（にげる PF2・育て屋 PF3・ちえくらべ MG2）。同じカードでも別の問い／たねポケモンもある手札（今のまま切り直さない）
- **依存・関係・競合**: 依存 なし／関係 PC-SETUP-MULLIGAN-COUNT／競合 なし
- **厳密モードとの差**: 厳密は今のまま準備で HALTED。プレイ用は切り直す（切り直しの回が増える）
- **影響**: 公開の情報 切り直しで手札を見せる（今の切り直しと同じ公開）／乱数 切り直しで山札を切る（乱数を使う）／コスト なし／処理の順番 変えない
- **共通処理で実装できる範囲**: engine._deal_opening_hands の HALTED の分岐を、規約の照会で切り直しに置きかえる
- **カード固有の対応が残る範囲**: 対象のカードの一覧（play_as_pokemon_in_hand が見るカード）を規約の対象に明示する
- **回帰テスト**: 化石・人形だけの手札で切り直すこと（回数・ログ・公開）／化石と人形とたねポケモンの手札が今と同じ／延長戦の区間でも同じ／厳密では今と同じ HALTED
- **推奨（案）**: 数えない（切り直す）（準備の規定の「たねポケモンカード」の語のまま当てはめ、最初のポケモンとして置く新しい処理（準備でのトレーナーの扱い）を作らない）
- **代替案**: 最初のポケモン（バトル場・ベンチ）として出せる（カードの「たねポケモンとして場に出せる」を準備にも当てはめる読み方。準備で置く処理の実装と、裏向きで置くときの扱いの確かめが要る（needs_implementation））
- **根拠**: docs/fossil-hidden-info-v0.47.md 3 章（PF1）／engine.py:491〜500。研究の記録: 裁定 PF1、kyuura の論点 UQ-PLAY-AS-POKEMON
- **未確認**: kyuura の UQ-PLAY-AS-POKEMON の記録の再照合（固定コミットの写しだけを見た）
- **判断事項**: DEC-PLAY-AS-POKEMON（状態 proposal）

#### PC-CHECK-SIDE-ORDER: ポケモンチェックで両方のプレイヤーが同じ処理をする順番

- **問い**: ポケモンチェック（どちらの番でもない）の同じ手順で、両方のプレイヤーがコインを投げる・処理をするとき、どちらから行うか
- **規約の文（案）**: ポケモンチェックの同じ手順で両方のプレイヤーが同じ種類の処理（ねむりのコイン・くろこげマーカーのコイン）をするときは、その番を終えたプレイヤー（ポケモンチェックの直前の番のプレイヤー）の場から先に、それぞれの場はバトル場 → ベンチの順に行う（今のログの順と同じ）
- **適用条件**: procedures.pokemon_check_sleep_and_paralysis で両方の対戦ポケモンがねむり（SLEEP_COIN_ORDER）、procedures._char_coin_stop で両方のプレイヤーがくろこげマーカーのコインを投げる（KK1）
- **対象の場面（続けられ方）**: `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（question_resolved_other_stops_possible）、`UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER`（question_resolved_other_stops_possible）、`UNRESOLVED_POKEMON_CHECK_BERRY_ORDER`（unverified）
- **除外・対象外の隣の場面**: ポケモンチェックの外の同時の処理（PC-ORDER-ATTACK-PRECHECK・PC-ORDER-OVERLAP）／両方のきぜつ（PC-CHECK-DOUBLE-KNOCKOUT）／サイドを取る順番（利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN は「同じきぜつの処理」の場面だけ。ポケモンチェックへ自動で広げない）
- **例外**: 片方のプレイヤーだけのコイン（今のまま）
- **依存・関係・競合**: 依存 なし／関係 PC-CHECK-DOUBLE-KNOCKOUT／競合 PC-ORDER-OVERLAP（ポケモンチェックの中に当てない。対象の一覧を分ける）
- **厳密モードとの差**: 厳密は今のまま HALTED。プレイ用はコインを投げて続ける
- **影響**: 公開の情報 変えない（コインは公開）／乱数 どちらのコインが乱数のどの値になるかが決まる（席・先攻後攻で偏らない: 番を終えたプレイヤーは毎回入れかわる）／コスト なし／処理の順番 ログの順と同じ
- **共通処理で実装できる範囲**: 2 か所の HALTED の分岐を、規約の照会で order（番を終えたプレイヤー → 相手）の順の処理に置きかえる。ねむりのコインの処理はすでに複数を順に扱う
- **カード固有の対応が残る範囲**: なし（くろこげマーカーのカードの一覧は今の登録のまま）
- **回帰テスト**: 両方ねむりの盤面で、コインの割り当て・回復・ログ（両方の番の終わりで）／両方のくろこげマーカーで、コインの前の確かめが今どおりはたらくこと／片方だけのときが今と同じ／厳密では今と同じ HALTED／道具の対戦で先攻・後攻の偏り（勝率の差）を測る
- **推奨（案）**: 番を終えたプレイヤーから（席（プレイヤー 0・1）によらず、ログの順・p.325 の「番のプレイヤー」に近い。決定を増やさない）
- **代替案**: 番を終えたプレイヤーが順番を選ぶ（決定を出す）（p.325 の決める人を当てはめる読み方。決定が増え、方策・ログが変わる）／次の番のプレイヤーから（席によらないが、根拠が弱い）
- **根拠**: procedures.py:925〜960（SLEEP_COIN_ORDER）／procedures.py:366〜388（KK1）／docs/pokemon-check-v0.3b.md／docs/marker-check-field-reset-v0.91.md 4 章。研究の記録: 裁定 BY1・KK1・Z29、kyuura の論点 UQ-POKEMON-CHECK-SLEEP-COIN-ORDER
- **未確認**: BY1 の順番の問いの中身（効果の種類の順番を含む）／勝率の偏りの計測はしていない
- **判断事項**: DEC-SLEEP-COIN-ORDER・DEC-ORDER-RULE（状態 proposal）

#### PC-CHECK-DOUBLE-KNOCKOUT: ポケモンチェックの両方のきぜつ

- **問い**: ポケモンチェックの「どく」などで両方のプレイヤーのポケモンがきぜつするとき、(1) 同時のきぜつか、(2) バトル場に出す順番、(3) サイドを取る順番を決める人
- **規約の文（案）**: (1) 同じポケモンチェックの 2 のダメージで両方のプレイヤーのポケモンがきぜつしたら、同時のきぜつとして扱う（勝ち負けは p.311 の表・サドン・デスを含む）。(2)(3) バトル場に出す順番・サイドを取る順番は、PC-CHECK-SIDE-ORDER と同じく番を終えたプレイヤーから（利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN を、この場面に当てるかは利用者が別に決める）
- **適用条件**: procedures._pokemon_check_plan が POKEMON_CHECK_DOUBLE_KNOCKOUT を返す条件（1・2 のあとに両方のプレイヤーの場に HP 以上のダメージのポケモンがいる）
- **対象の場面（続けられ方）**: `UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`（partial）
- **除外・対象外の隣の場面**: ワザの処理の中の同時のきぜつ（利用者の指定 USER-PRIZE-ORDER-* が今のまま扱う）／ポケモンチェックの途中のきぜつ（PC-CHECK-KO-POINT）
- **依存・関係・競合**: 依存 PC-CHECK-SIDE-ORDER／関係 CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN・CONV:USER-PRIZE-ORDER-PER-PLAYER／競合 なし
- **厳密モードとの差**: 厳密は今のまま、ダメージの前に HALTED。プレイ用はダメージを与え、両方のきぜつの処理に進む
- **影響**: 公開の情報 サイドの取り方は今の公開の範囲（v0.140 のまま）／乱数 なし（コインを使わない）／コスト なし／処理の順番 バトル場に出す・サイドを取る順番が決まる
- **共通処理で実装できる範囲**: ポケモンチェックの続き（then が次の番）で、両方のプレイヤーのサイド・バトル場に出す決定の並びを作る（v0.140 はこの場面で prize_first を出さない）
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 両方どくで両方きぜつする盤面で、勝ち負け・サドン・デス・サイドの並び・バトル場に出す順番／片方だけのきぜつが今と同じ／厳密では今と同じ HALTED
- **推奨（案）**: (1) 同時のきぜつとして扱う。(2)(3) は PC-CHECK-SIDE-ORDER にしたがう（p.324 の同時の勝利条件の扱いと合う。決める人は PC-CHECK-SIDE-ORDER と同じにして規約の数を増やさない）
- **代替案**: (3) に利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN を広げる（番を終えたプレイヤーに決定を出す）（利用者の指定の範囲を変えることになるので、利用者の明示の承認が要る）／番を終えたプレイヤーのポケモンが先にきぜつ（同時ではない）（ポケモンチェックの 2 のダメージは同時に与えるので、根拠が弱い）
- **根拠**: procedures.py:70〜78・_pokemon_check_plan／docs/prize-order-user-rule-v0.140.md 2 章（ポケモンチェックの続きでは出さない）。研究の記録: 裁定 —、kyuura の論点 —
- **未確認**: ポケモンチェックの続きの両方のサイドの処理を作る実装の量
- **判断事項**: DEC-KNOCKOUT-READINGS・DEC-ORDER-RULE（状態 proposal）

#### PC-CHECK-KO-POINT: ポケモンチェックの途中のきぜつの判定の時点

- **問い**: ポケモンチェックの 1（悪エネルギー・くろこげマーカー・きのみ）と 2（どく）のあいだで HP 以上のダメージになったポケモンを、いつきぜつさせるか
- **規約の文（案）**: ポケモンチェックの 1・2 の途中ではきぜつを判定しない。2 のあとに 1 回だけ判定する（2 の処理は 1 のあとの場で行い、HP 以上のダメージのポケモンにもどくのダメージを与える）
- **適用条件**: procedures.mid_check_knockout_divergence が違いを返す（1 のあとに HP 以上になったポケモンがいて、判定の時点で結果が変わる）
- **対象の場面（続けられ方）**: `UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`（unverified）
- **除外・対象外の隣の場面**: 2 のあとのきぜつ（今のまま）／ワザの処理の中のきぜつ
- **依存・関係・競合**: 依存 なし／関係 PC-CHECK-DOUBLE-KNOCKOUT／競合 なし
- **厳密モードとの差**: 厳密は今のまま HALTED
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 きぜつの判定の時点
- **共通処理で実装できる範囲**: _pokemon_check_plan の PK1 の分岐を、規約の照会で 2 のあとの判定に置きかえる
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 1 で HP 以上になったポケモンがどく状態のときの、ダメージ・きぜつ・ログ／厳密では今と同じ
- **推奨（案）**: 2 のあとに 1 回だけ判定（p.323 の手順の番号順で、途中に判定の手順がない）
- **代替案**: 1 のあとにも判定する（手順の途中にきぜつの判定を加える読み方）
- **根拠**: procedures.py の _pokemon_check_plan・docs/darkness-metal-energy-v0.78.md 6 章。研究の記録: 裁定 PK1、kyuura の論点 —
- **未確認**: mid_check_knockout_divergence のほかの条件
- **判断事項**: DEC-KNOCKOUT-READINGS（状態 proposal）

#### PC-COIN-COUNT-SHORT: コインで決まった枚数が足りないとき（途中停止の 2 つ）

- **問い**: コインの「おもて」の数で決まった枚数のエネルギーをトラッシュする効果で、対象のエネルギーが足りないとき、どうするか
- **規約の文（案）**: コインの結果で決まった枚数が、その時点の対象の枚数より多いときは、対象をすべて処理し、足りない分は何もしない（コインの結果・ほかの処理は変えない）
- **適用条件**: 共通の数量処理（check_quantity）で DeferredShortage が起こる場面のうち、DU1（ひからびさせる）・TW1（思念波マシーン）
- **対象の場面（続けられ方）**: `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`（unverified）、`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT`（unverified）
- **除外・対象外の隣の場面**: ひかるバンギラス neo4-082 の 2 つのワザ（利用者の指定のまま。この規約の根拠にしない・指定を広げない）／使う前に決まった枚数が足りない（PC-STATED-COUNT-SHORT）／すでに途中停止した保存状態の再開（DEC-DEFERRED-RESUME。この規約は再開の操作を作らない）
- **依存・関係・競合**: 依存 なし／関係 PC-STATED-COUNT-SHORT・POLICY:user_specified_rules:neo4-082/attack/0・POLICY:user_specified_rules:neo4-082/attack/1／競合 なし
- **厳密モードとの差**: 厳密は今のまま途中停止（コインのあとの終端）。プレイ用は止めずに続ける
- **影響**: 公開の情報 なし（枚数は公開）／乱数 コインはどちらでも投げる（同じ）／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: engine._interrupted に渡す DeferredShortage を、規約の照会で「あるだけ」の処理に置きかえる（共通の数量処理のチェック地点）
- **カード固有の対応が残る範囲**: なし（チェック地点はカードの登録が持つ）
- **回帰テスト**: 足りない盤面での処理・ログ／足りる盤面が今と同じ／厳密では今と同じ途中停止
- **推奨（案）**: あるだけ処理する（コインのあとなので「使えない」にできず、途中停止のまま再開の操作もない（GAP-DEFERRED-HALT-NO-RESUME））
- **代替案**: 効果全体を何もしない（足りなければトラッシュしない）（結果が大きく変わる。根拠が弱い）
- **根拠**: docs/deferred-shortage-user-promos-v0.127.md 5 章／engine.py の DeferredShortage の捕まえ方。研究の記録: 裁定 DU1・TW1、kyuura の論点 UQ-STATED-COUNT-SHORT
- **未確認**: 2 つのチェック地点の後の処理（あるだけにしたあとの続き）をコードで確かめていない
- **判断事項**: DEC-STATED-COUNT-SHORT・DEC-DEFERRED-RESUME（状態 proposal）

#### PC-STATED-COUNT-SHORT: 説明の決まった枚数が公開の枚数より多いとき

- **問い**: 説明が決まった枚数（山札の上から N 枚など）を処理させるのに、使う時点でその場所の枚数が足りないとき、使えるか・どれだけ処理するか
- **規約の文（案）**: 使う時点で、その場所の公開の枚数が説明の枚数より少ないときは、使える。その場所のカードをすべて処理し、足りない分は何もしない
- **適用条件**: 使う前の確かめで、山札・手札・場などの公開の枚数（中身ではなく枚数）が説明の枚数に足りずに止める場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_ATTACK_DECK_TOP_SHORT`（unverified）、`UNRESOLVED_DECK_TOP_SHORT`（unverified）、`UNRESOLVED_DISCARD_DECK_SHORT`（unverified）、`UNRESOLVED_FLASH_DECK_SHORT`（unverified）、`UNRESOLVED_MASTER_BALL_SHORT_DECK`（unverified）、`UNRESOLVED_MISTYS_WRATH_SHORT_DECK`（unverified）、`UNRESOLVED_POWER_DECK_TOP_SHORT`（unverified）、`UNRESOLVED_STATED_CARDS_SHORT#public-counts`（unverified）、`UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER`（unverified）
- **除外・対象外の隣の場面**: 山札の中身（目的のカードの有無・枚数）で決まる場面（PC-HIDDEN-SEARCH-EMPTY。STATED_CARDS_SHORT#deck-contents）／コインのあとに分かる不足（PC-COIN-COUNT-SHORT）／ひかるバンギラス neo4-082（利用者の指定のまま）
- **例外**: フラッシュ FU1 はおもての山札の問い（PC-FACE-UP-DECK）と重なる。重ねる場合の扱いは FU の規約と組で決める
- **依存・関係・競合**: 依存 なし／関係 PC-COIN-COUNT-SHORT／競合 なし
- **厳密モードとの差**: 厳密は今のまま使う前に拒否。プレイ用は使える
- **影響**: 公開の情報 なし（枚数は公開）／乱数 使えるようになったカードのコインを投げる／コスト カードのトラッシュ・回数の消費が増える／処理の順番 なし
- **共通処理で実装できる範囲**: 使う前の確かめの拒否を、規約の照会で外し、効果の処理を「あるだけ」にする（効果の型ごとの処理が要る場合がある）
- **カード固有の対応が残る範囲**: 効果の型ごとの「あるだけ」の処理（山札の上・手札・場で別の処理）
- **回帰テスト**: 足りない盤面での受け付け・処理・ログ・観測／足りる盤面が今と同じ／厳密では今と同じ拒否／対の比べ（枚数だけで決まり、中身によらない）
- **推奨（案）**: 使える（あるだけ処理する）（枚数は公開で、秘密に依存しない。PC-COIN-COUNT-SHORT と同じ扱いにそろう）
- **代替案**: 使えない（今の拒否を規約にする）（挙動は今と同じ。止める場面の記録を規約に変えるだけ）
- **根拠**: 台帳の PF-STATED-COUNT-SHORT の候補 P-SCS-1・P-SCS-2。研究の記録: 裁定 FC1・FU1・HC6・LT1・ML1・MW1・OB1・TOP1・VG1、kyuura の論点 UQ-STATED-COUNT-SHORT
- **未確認**: 各コードの拒否が枚数だけで決まるか（中身を読まないか）を、箇所ごとに確かめていない
- **判断事項**: DEC-STATED-COUNT-SHORT（状態 proposal）

#### PC-USE-WITHOUT-TARGET: 選ぶ対象が最初からないときに使えるか

- **問い**: 説明が選ばせる対象（控え・場のポケモン・トラッシュのカード・手札など）が、使う宣言の時点で 1 つもないときに、カード・特殊能力・スタジアムを使えるか
- **規約の文（案）**: 使う宣言の時点で、説明が選ばせる対象が公開の領域（場・トラッシュ）と使う人の手札に 1 つもないときは、使えない（宣言を受け付けない。状態・乱数・ログを変えない。トラッシュ・回数の消費・コインもない）
- **適用条件**: 使う前の確かめ（check_playable・check_usable・check_activation）が、対象の一覧が空であることだけを理由に止める場面。対象の有無が公開の情報と使う人の手札だけで決まるもの
- **対象の場面（続けられ方）**: `UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET`（unverified）、`UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON`（unverified）、`UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`（unverified）、`UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET`（unverified）、`UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET`（unverified）、`UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET`（unverified）、`UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`（unverified）、`UNRESOLVED_ENERGY_STADIUM_WITHOUT_TARGET`（unverified）、`UNRESOLVED_FOSSILIZE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_FOSSIL_GUIDE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET`（unverified）、`UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`（unverified）、`UNRESOLVED_LAST_RESORT_WITHOUT_TARGET`（unverified）、`UNRESOLVED_LT_SURGE_WITHOUT_BASIC`（unverified）、`UNRESOLVED_MAX_REVIVE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_MISTYS_CARE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_MISTYS_WISH_WITHOUT_HAND`（unverified）、`UNRESOLVED_MR_FUJI_WITHOUT_BENCH`（unverified）、`UNRESOLVED_OLD_ROD_WITHOUT_TARGET`（unverified）、`UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_POWER_COUNTER_MOVE_WITHOUT_COUNTERS`（unverified）、`UNRESOLVED_POWER_RETURN_WITHOUT_TARGET`（unverified）、`UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH`（unverified）、`UNRESOLVED_REVIVE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH`（unverified）、`UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON`（unverified）、`UNRESOLVED_SCOOP_UP_LAST_POKEMON`（unverified）、`UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET#discard`（unverified）、`UNRESOLVED_SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET`（unverified）、`UNRESOLVED_SUPER_ROD_WITHOUT_TARGET`（unverified）、`UNRESOLVED_SWITCH_WITHOUT_BENCH`（unverified）、`UNRESOLVED_THOUGHT_WAVE_MACHINE_WITHOUT_TARGET`（unverified）、`UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET`（unverified）、`UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET#public-zones`（unverified）、`UNRESOLVED_TRAINER_WITHOUT_TARGET`（unverified）、`UNRESOLVED_TRANSPORT_WITHOUT_CARDS`（unverified）、`UNRESOLVED_WANT_WITHOUT_TARGET`（unverified）、`UNRESOLVED_NINJA_GYM_WITHOUT_TARGET`（blocked_by_defect）
- **除外・対象外の隣の場面**: 山札（非公開）を探す場面（PC-HIDDEN-SEARCH-EMPTY）／対象はあるが何も起こらない場面（PC-USE-WITHOUT-EFFECT・PC-CHOOSE-TARGET-WITHOUT-EFFECT）／効果の途中で対象がいなくなる場面（PC-TARGET-LOST-MID-EFFECT）／コストを払えない場面（個別。PW2）／「最大N」の 0（PC-UP-TO-ZERO）
- **例外**: コインだけを投げて使い終われるかの問い（BP1・EN1・FG2・GU1・SX1・WT1・VN1・HF1 など。コインのあとに対象を選ぶ）も、この規約では「使えない」（コインを投げない）／kyuura・エンジンの記録が「ほかのカードの答えを流用しない」と書くカード（RG1・SU2・HY1 など）は、規約の対象の一覧で個別に承認する（一括の承認にしない）
- **依存・関係・競合**: 依存 なし／関係 PC-HIDDEN-SEARCH-EMPTY／競合 なし
- **厳密モードとの差**: 挙動の差はない（今の拒否と同じ）。プレイ用では、止める理由が未決の裁定から規約による拒否に変わる（記録・ログの区別だけ）
- **影響**: 公開の情報 変えない（今の拒否と同じ。対象の有無は公開・本人の手札で決まる）／乱数 変えない／コスト 変えない／処理の順番 なし
- **共通処理で実装できる範囲**: 止める箇所に事例の識別と規約の照会を加え、規約があれば「規約による拒否」（未決の裁定の停止と区別した記録）にする。処理は変えない
- **カード固有の対応が残る範囲**: なし（対象の一覧の承認だけ）
- **回帰テスト**: 対象のない盤面で、拒否の種類・状態・乱数・ログが変わらない／対象がある盤面が今と同じ／対の比べ（公開・本人の手札だけで決まる）
- **推奨（案）**: 使えない（今の挙動のまま（実装・乱数・情報の変更がない）。拒否は対戦を止めない（ほかの操作を選べる）ので、続行の効果は記録の区別だけ）
- **代替案**: 使える（カードはトラッシュ・回数は消費・コインは投げる。対象のない部分は何もしない）（台帳の P-UWE-2。山札を減らす・コインを投げる使い方が増える。効果の型ごとの処理が要る）
- **根拠**: 台帳の PF-USE-WITHOUT-EFFECT の候補 P-UWE-1・P-UWE-2／各コードの理由の文（effects.py の *_REASON）。研究の記録: 裁定 BE2・BP1・CS6・DV4・EM1・EN1・ER10・FG2・FJ1・FS1・FT1・GL1・GU1・GW5・HY1・LS1・MQ2・MR1・MY1・NJ1・OR1・PW1・QZ1・RG1・RV1・SB1・SR1・SRD1・ST1・SU2・SX1・TN1・TR1・TW2・UPZ2・VN1・WT1、kyuura の論点 UQ-CARD-USE-WITHOUT-TARGET・UQ-COMPUTER-SEARCH-EMPTY-DECK・UQ-ENERGY-RETRIEVAL-WITHOUT-TARGET・UQ-GUST-WITHOUT-OPPONENT-BENCH
- **未確認**: 各コードの止める条件が対象の有無だけで、公開・本人の手札だけで決まることを、箇所ごとに比べの道具で確かめていない（NJ1 の漏れは見つけた）
- **判断事項**: DEC-USE-WITHOUT-EFFECT（状態 proposal）

#### PC-HIDDEN-SEARCH-EMPTY: 山札を探す効果で、目的のカードが見つからないとき

- **問い**: 山札（非公開）から決まったカードを選ぶ効果を、山札に目的のカードがないかもしれないとき（本人に見えない）に使えるか。見つからなければどうなるか
- **規約の文（案）**: 山札から決まったカードを選ぶ効果は、山札にカードが 1 枚以上あれば使える（目的のカードの有無で使えるかを変えない）。山札を見て目的のカードがなければ何も選ばず、説明のほかの処理（山札を切るなど）を行う
- **適用条件**: 使う前の確かめが、山札の中身の下限（effects.deck_target_lower_bound・bench_entry_unconfirmed）で止める場面（事例の secret_dependency が owner_known_pool・depends_on_hidden_static）
- **対象の場面（続けられ方）**: `UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET#deck`（needs_secret_review）、`UNRESOLVED_STATED_CARDS_SHORT#deck-contents`（needs_secret_review）、`UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET#amplifier-deck`（needs_secret_review）、`UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK#coin-evolve-self-from-deck`（blocked_by_defect）
- **除外・対象外の隣の場面**: 公開の領域（トラッシュ）を探す場面（PC-USE-WITHOUT-TARGET）／山札の枚数（公開）が足りない場面（PC-STATED-COUNT-SHORT）
- **例外**: 山札が 0 枚（公開）のときは PC-USE-WITHOUT-TARGET と同じ（使えない）
- **依存・関係・競合**: 依存 なし／関係 PC-USE-WITHOUT-TARGET／競合 なし
- **厳密モードとの差**: 厳密は今の保守的な下限で止める。プレイ用は使えて、見つからなければ何も選ばない
- **影響**: 公開の情報 使う人だけが山札を見る（見つからないことは使う人にだけ分かる。相手には何も選ばなかったことが公開）／乱数 山札を切る説明なら乱数を使う／コスト カードのトラッシュ・回数の消費／処理の順番 なし
- **共通処理で実装できる範囲**: 探して見つからない処理（決定の 0 個の答え・ログ）を共通にする。下限の確かめを規約の照会で外す
- **カード固有の対応が残る範囲**: 効果の型ごとの見つからないときの続き（山札を切る・手札に加えないなど）
- **回帰テスト**: 目的のカードが山札・サイドにある 2 盤面の対の比べ（受理・拒否・理由・候補が同じ）／見つからないときのログ・観測（相手に中身が伝わらない）／厳密では今と同じ
- **推奨（案）**: 使える（見つからなければ何も選ばない）（受け付けが山札の配分によらないので、v0.137・v0.138 の下限による保守的な制限より秘密に強い。実際の対戦の扱いに近い）
- **代替案**: 今の下限で止める（規約にする）（挙動は今と同じ。保守的に使えない場面が残る）
- **根拠**: docs/deck-search-oracle-v0.137.md／docs/oracle-leak-fixes-v0.138.md／台帳の事例の secret_dependency。研究の記録: 裁定 FC1・GV1・ST1・UPZ2、kyuura の論点 UQ-CARD-USE-WITHOUT-TARGET・UQ-EVOLUTION-PERMISSION-FROM-DECK・UQ-STATED-COUNT-SHORT
- **未確認**: 見つからない処理の実装の量／GV1 の経路の漏れの比べ（未確認）
- **判断事項**: DEC-USE-WITHOUT-EFFECT・DEC-INFO-LEAK-FIXES（状態 proposal）

#### PC-USE-WITHOUT-EFFECT: 使っても何も起こらないときに使えるか

- **問い**: 回復・特殊状態の回復など、使っても何も起こらない（ダメージ・特殊状態がない）ときに、カード・特殊能力を使えるか
- **規約の文（案）**: 使う宣言の時点で、効果が当たりうるポケモン（ダメージカウンター・特殊状態のあるポケモン）が 1 匹もいないときは、使えない（宣言を受け付けない。状態・乱数・ログを変えない）
- **適用条件**: 使う前の確かめが、効果の起こるポケモンがいないことだけを理由に止める場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_POTION_WITHOUT_DAMAGE`（unverified）、`UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION`（unverified）、`UNRESOLVED_SOLAR_POWER_WITHOUT_CONDITION`（unverified）、`UNRESOLVED_HELPING_HAND_WITHOUT_CONDITION`（unverified）、`UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION`（unverified）、`UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE`（unverified）、`UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE`（unverified）
- **除外・対象外の隣の場面**: 選ぶ対象そのものがない場面（PC-USE-WITHOUT-TARGET）／効果のないポケモンを選べるか（PC-CHOOSE-TARGET-WITHOUT-EFFECT）
- **例外**: ばんのうごな BP1 は、ダメージと特殊状態の片方だけがあればある方を処理する（今のまま）。両方ないときは PC-USE-WITHOUT-TARGET の対象として記録した
- **依存・関係・競合**: 依存 なし／関係 PC-CHOOSE-TARGET-WITHOUT-EFFECT・PC-USE-WITHOUT-TARGET／競合 なし
- **厳密モードとの差**: 挙動の差はない（今の拒否と同じ）。止める理由の記録だけが変わる
- **影響**: 公開の情報 変えない（ダメージ・特殊状態は公開）／乱数 変えない／コスト 変えない／処理の順番 なし
- **共通処理で実装できる範囲**: PC-USE-WITHOUT-TARGET と同じ（規約による拒否の記録）
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 何も起こらない盤面で、拒否・状態・乱数・ログが変わらない／起こる盤面が今と同じ
- **推奨（案）**: 使えない（今の挙動のまま。拒否は対戦を止めない）
- **代替案**: 使える（カードをトラッシュし、回数を消費し、何もしない）（ジム・特殊能力の「番に 1 回」を使い切る使い方が増える）
- **根拠**: kyuura の UQ-TARGET-WITHOUT-EFFECT・UQ-CARD-USE-WITHOUT-TARGET（台帳の研究の記録）。研究の記録: 裁定 FH2・HC8・HF1・HH1・SO1・TG1、kyuura の論点 UQ-CARD-USE-WITHOUT-TARGET・UQ-TARGET-WITHOUT-EFFECT
- **未確認**: 箇所ごとの止める条件
- **判断事項**: DEC-USE-WITHOUT-EFFECT（状態 proposal）

#### PC-CHOOSE-TARGET-WITHOUT-EFFECT: 選んでも何も起こらないポケモンを選べるか

- **問い**: 回復などの対象を選ぶとき、ダメージカウンターののっていないポケモン（選んでも何も起こらない）を選べるか
- **規約の文（案）**: 効果の対象を選ぶときは、選んで効果が起こるポケモンがいる限り、何も起こらないポケモンは選べない（候補に出さない）
- **適用条件**: 対象の選び方の確かめで、選んだポケモンに効果が起こらないことを理由に止める場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_POTION_UNDAMAGED_TARGET`（unverified）、`UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET`（unverified）、`UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET`（unverified）、`UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY`（unverified）、`UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET`（unverified）
- **除外・対象外の隣の場面**: 効果が起こるポケモンが 1 匹もいない（PC-USE-WITHOUT-EFFECT）
- **依存・関係・競合**: 依存 PC-USE-WITHOUT-EFFECT／関係 なし／競合 なし
- **厳密モードとの差**: 今の止め方（どの経路で止めるかはコードごと）を規約による候補の制限に変える
- **影響**: 公開の情報 変えない（公開）／乱数 変えない／コスト 変えない／処理の順番 なし
- **共通処理で実装できる範囲**: 候補の作り方に規約の照会を加える（候補を黙って減らさない: 規約で減らしたことを記録する）
- **カード固有の対応が残る範囲**: 候補の作り方はカードの型ごと
- **回帰テスト**: 効果のあるポケモンとないポケモンがいる盤面で、候補・答えの受け付け／厳密では今と同じ
- **推奨（案）**: 選べない（候補を減らすだけで、乱数・情報は変わらない）
- **代替案**: 選べる（何も起こらない）（いいきずぐすりのエネルギーのトラッシュなど、効果の一部だけを使う使い方が増える（効果の型ごとに結果が違う））
- **根拠**: kyuura の UQ-TARGET-WITHOUT-EFFECT（台帳の研究の記録）。研究の記録: 裁定 GL2・MK1・SB2・SP1、kyuura の論点 UQ-TARGET-WITHOUT-EFFECT
- **未確認**: 箇所ごとの止め方（使う前の拒否か、答えの拒否か）
- **判断事項**: DEC-USE-WITHOUT-EFFECT（状態 proposal）

#### PC-UP-TO-ZERO: 「最大N」「好きなだけ」で 0 を選べるか

- **問い**: 「最大 N 枚」「好きなだけ」で選ぶとき、選べる候補があっても 0 を選べるか
- **規約の文（案）**: 「最大 N」「好きなだけ」と書かれた選び方では、選べる候補があっても 0 を選べる（0 を選んだら、その選び方の結果の処理だけを行わない）
- **適用条件**: 答えの確かめが 0 個の答えを止める場面（台帳の PF-UP-TO-ZERO。止め方は answer_rejection）
- **対象の場面（続けられ方）**: `UNRESOLVED_ATTACH_FROM_DISCARD_ZERO`（unverified）、`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`（unverified）、`UNRESOLVED_DISCARD_ANY_NUMBER_ZERO`（unverified）、`UNRESOLVED_DISCARD_UP_TO_ZERO`（unverified）、`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`（unverified）、`UNRESOLVED_HEAL_UP_TO_ZERO`（unverified）、`UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE`（unverified）、`UNRESOLVED_POKEDEX_UP_TO_ZERO`（unverified）、`UNRESOLVED_RECOVER_ZERO_ENERGY`（unverified）、`UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE`（unverified）、`UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE`（unverified）、`UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE`（unverified）、`UNRESOLVED_POWER_ZERO_CARDS`（blocked_by_defect）
- **除外・対象外の隣の場面**: 「N 枚」（最大と書かれていない）／選べる候補がない場面（PC-USE-WITHOUT-TARGET）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま 0 個の答えを受け付けない（ほかの答えは受け付ける）。プレイ用は 0 個も受け付ける
- **影響**: 公開の情報 変えない（候補は今のまま）／乱数 なし／コスト 使う宣言のコストは今のまま／処理の順番 なし
- **共通処理で実装できる範囲**: 答えの確かめの 0 個の拒否を、規約の照会で受け付けに変える（答えの範囲の確かめは共通の部品）
- **カード固有の対応が残る範囲**: 0 個のときの続き（山札を切るか・ログ）がカードの型ごとに違う場合がある
- **回帰テスト**: 0 個の答えの受け付け・続き・ログ／1 個以上の答えが今と同じ／厳密では今と同じ
- **推奨（案）**: 0 を選べる（「最大」の語のまま。答えの範囲が広がるだけで、乱数・情報は変わらない）
- **代替案**: 候補があれば 1 以上（今の拒否を規約にする）（挙動は今と同じ）
- **根拠**: 台帳の PF-UP-TO-ZERO の候補 P-UTZ-1・P-UTZ-2／kyuura の UQ-UP-TO-ZERO-CHOICE。研究の記録: 裁定 ER9・GS1・H4・HC5・HC7・HZ1・NG1・PD2・PW3・RKB1・RT1・SR2・UPZ1、kyuura の論点 UQ-ENERGY-CONVERSION-ZERO・UQ-ENERGY-RETRIEVAL-ZERO-CHOICE・UQ-UP-TO-ZERO-CHOICE
- **未確認**: 0 個のときの続きをコードごとに確かめていない
- **判断事項**: DEC-UP-TO-ZERO（状態 proposal）

#### PC-NON-ATTACK-DAMAGE-MODIFIERS: ワザ以外のダメージに、ダメージを変える効果を当てはめるか

- **問い**: ワザのダメージでないダメージ（どく・こんらんの自分へのダメージ・特殊能力・トレーナー・スタジアム・エネルギーのダメージ）に、受けるダメージ・与えるダメージを変える効果を当てはめるか
- **規約の文（案）**: ワザのダメージでないダメージには、ダメージの量を変える効果（受けるダメージ・与えるダメージを変える特殊能力・トレーナー・エネルギー・持続する効果）を当てはめない。その効果の説明が、そのダメージを名指ししている場合だけ当てはめる
- **適用条件**: ワザ以外のダメージの量を求めるとき、量を変える効果があって、当てはめるかで量が変わる場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`（unverified）、`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`（unverified）、`UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER`（unverified）、`UNRESOLVED_INFLATE_NON_ATTACK_DAMAGE`（unverified）、`UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER`（unverified）、`UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER`（unverified）、`UNRESOLVED_TRAINER_DAMAGE_REDUCTION`（unverified）、`UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER`（unverified）、`UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE`（unverified）、`UNRESOLVED_GROWL_NON_ATTACK_DAMAGE`（unverified）
- **除外・対象外の隣の場面**: 弱点・抵抗力（PC-UNSTATED-WEAKNESS-RESISTANCE）／ワザのダメージ（今のまま）／効果を当てはめる順番（鋼エネルギーと特殊能力の MT1 など。個別）／説明に「〜に関係なく」とあるダメージ（今のまま当てはめない）
- **例外**: くろこげマーカーのダメージの FA1（「その他の効果」に関係なく）の読み方は別の問い（個別）
- **依存・関係・競合**: 依存 なし／関係 PC-UNSTATED-WEAKNESS-RESISTANCE／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否・HALTED（KA1）。プレイ用は当てはめずに続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 なし（量だけ）
- **共通処理で実装できる範囲**: ワザ以外のダメージの計算の共通の部品（ダメージの量の問い合わせ）に、規約の照会を加える
- **カード固有の対応が残る範囲**: 名指しの判定（説明がそのダメージを名指ししているか）はカードの登録ごと
- **回帰テスト**: どく・こんらん・特殊能力・トレーナーのダメージで、量・ログ／ワザのダメージが今と同じ／厳密では今と同じ
- **推奨（案）**: 当てはめない（p.321 のダメージの計算はワザによるダメージの手順で、ワザ以外のダメージの手順はない。こんらんの自分へのダメージ（道具の対戦で拒否が多い）も含めて、1 つの規約で扱える）
- **代替案**: 受けるダメージを変える効果だけ当てはめる（与える側は当てはめない）（「受けるダメージ」の語を広く読む読み方。効果の種類で分ける必要がある）／すべて当てはめる（ワザのダメージと同じに扱う読み方）
- **根拠**: kyuura の UQ-NON-ATTACK-DAMAGE-MODIFIERS（6 コード）／procedures.py の POISON_RECEIVED_POWER（KA1）。研究の記録: 裁定 DB1・DE1・DF2・EX1・GN1・IF1・KA1・RB4・TD1、kyuura の論点 UQ-GROWL-NON-ATTACK-DAMAGE・UQ-NON-ATTACK-DAMAGE-MODIFIERS
- **未確認**: コードごとに、規約を当てた後の処理に別の停止がないか
- **判断事項**: DEC-DAMAGE-READINGS（状態 proposal）

#### PC-UNSTATED-WEAKNESS-RESISTANCE: 「弱点・抵抗力に関係なく」と書かれていないワザ以外・控えへのダメージの弱点・抵抗力

- **問い**: 説明に「弱点・抵抗力」に関係なく、と書かれていない、控えへのワザのダメージ・特殊能力のダメージに、弱点・抵抗力を計算するか
- **規約の文（案）**: 弱点・抵抗力は、ワザで相手の対戦ポケモンに与えるダメージだけに計算する。控えへのダメージ・特殊能力のダメージには、説明に書かれていなくても計算しない
- **適用条件**: 控えへのワザのダメージ（JS1）・特殊能力のダメージ（Z9）で、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプのときだけ（今の止める条件）
- **対象の場面（続けられ方）**: `UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`（unverified）、`UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE`（unverified）
- **除外・対象外の隣の場面**: ワザの対戦ポケモンへのダメージ（今のまま計算する）／英語版の「Apply Weakness and Resistance」を根拠にしない
- **依存・関係・競合**: 依存 なし／関係 PC-NON-ATTACK-DAMAGE-MODIFIERS／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は計算しないで続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 弱点・抵抗力の計算の部品に規約の照会を加える
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 控え・特殊能力のダメージの量／対戦ポケモンへのワザのダメージが今と同じ
- **推奨（案）**: 計算しない（p.321 の計算の手順はワザの対戦ポケモンへのダメージ）
- **代替案**: 計算する（書かれていない以上は通常の計算をする読み方）
- **根拠**: effects.py の POWER_DAMAGE_WR_REASON（Z9）／kyuura の UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE・UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE。研究の記録: 裁定 JS1・Z9、kyuura の論点 UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE・UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE
- **未確認**: JS1 が控えへのワザのダメージのどの説明の型か（コードで確かめていない）
- **判断事項**: DEC-DAMAGE-READINGS（状態 proposal）

#### PC-SPECIAL-ENERGY-CARD-WORDING: 特殊エネルギーカードは「X エネルギーカード」か

- **問い**: レインボーエネルギー・ミラクルエネルギーなど、X のエネルギーを出す特殊エネルギーカードを、説明の「X エネルギーカード」「基本エネルギーカード」に数えるか
- **規約の文（案）**: 説明の「X エネルギーカード」（カードを指す語）には、基本 X エネルギーカードだけが当たる。特殊エネルギーカードは、場で X のエネルギーを出していても当たらない。「X エネルギー」（出しているエネルギーを指す語）は、今のとおり出しているエネルギーで数える
- **適用条件**: 説明が「X エネルギーカード」を数える・選ぶ・トラッシュする場面で、特殊エネルギーカードが X を出していて、数えるかで結果が変わる（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE`（unverified）、`UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD`（unverified）、`UNRESOLVED_RAINBOW_ATTACH_AS_TYPE`（unverified）、`UNRESOLVED_RAINBOW_ENERGY_TYPE`（unverified）、`UNRESOLVED_TRANSFORM_SPECIAL_ENERGY`（unverified）、`UNRESOLVED_MIRACLE_ENERGY_AS_TYPE`（unverified）、`UNRESOLVED_RAINBOW_RECOVER_AS_TYPE`（unverified）、`UNRESOLVED_FERVOR_RAINBOW_ENERGY`（unverified）、`UNRESOLVED_COLOR_CHANGED_ENERGY_CARD`（unverified）
- **除外・対象外の隣の場面**: 色を変える効果の続く間・順番（CE1・CE2・VS1。個別）／きせきのかぜ（WD1・WD2・MEW1。個別）／にげるのコストの払い方（PC-RETREAT-COST-PAYMENT）
- **例外**: ［エネエネ］で役割が変わったカード（BZ2）は、役割の記録の読み方と組（コードで確かめていない）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は基本エネルギーカードだけを数えて続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト トラッシュするカードの選び方が変わる／処理の順番 なし
- **共通処理で実装できる範囲**: エネルギーカードの種類を数える共通の部品に規約の照会を加える
- **カード固有の対応が残る範囲**: 特殊エネルギーカードの登録ごとの役割
- **回帰テスト**: レインボー・ミラクルがついた盤面で、数え方・選べる候補／基本エネルギーだけの盤面が今と同じ
- **推奨（案）**: 基本 X エネルギーカードだけ（カードを指す語と出しているエネルギーを指す語を分ける読み方で、ほかのカードの記録と合わせやすい）
- **代替案**: 場で X を出しているあいだは X エネルギーカードとして数える（場と場の外で数え方が変わる）
- **根拠**: kyuura の UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY（5 コード）。研究の記録: 裁定 BZ2・CE3・FV1・MEC1・RB1・RB2・RB3・RB5・TE2、kyuura の論点 UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY
- **未確認**: コードごとの止める条件（数え方の違いだけか）
- **判断事項**: DEC-ENERGY-READINGS（状態 proposal）

#### PC-RETREAT-COST-PAYMENT: にげるのコストの払い方

- **問い**: にげるのコストを、出すエネルギーが 2 個以上のカードで払うとき余ってよいか、コストを減らす効果で 0 より小さくなるとき
- **規約の文（案）**: にげるのコストは、トラッシュするエネルギーカードの出すエネルギーの合計がコスト以上になるように払う。どのカードを除いてもコストに足りなくなる組だけを選べる（余りは捨てる）。コストを減らす効果で 0 より小さくなったら 0
- **適用条件**: にげるで、トラッシュするエネルギーの出すエネルギーがコストより多い（RT1）・コストの計算が 0 を下回る（CP2）
- **対象の場面（続けられ方）**: `UNRESOLVED_RETREAT_OVERPAY`（unverified）、`UNRESOLVED_RETREAT_COST_FLOOR`（unverified）
- **除外・対象外の隣の場面**: ワザのエネルギーのコスト（今のまま）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は払い方の決まりで続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト トラッシュするカード／処理の順番 なし
- **共通処理で実装できる範囲**: にげるのコストの確かめ（共通の手順）に規約の照会を加える
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 2 個のエネルギーを出すカードで 1 のコストを払う盤面／通常のにげるが今と同じ
- **推奨（案）**: 最小の組で払い、余りは捨てる。0 を下回ったら 0（1 つの手順の中の 2 つの問いで、同じ論点（kyuura の UQ-RETREAT-COST-PAYMENT））
- **代替案**: 余るカードでは払えない（出すエネルギーの多いカードではにげられない場面が出る）
- **根拠**: kyuura の UQ-RETREAT-COST-PAYMENT。研究の記録: 裁定 CP2・RT1、kyuura の論点 UQ-RETREAT-COST-PAYMENT
- **未確認**: 2 つのコードの止める条件の細部
- **判断事項**: DEC-ENERGY-READINGS（状態 proposal）

#### PC-NULLIFIED-ELEMENT-COIN: 効果がはたらかない要素のコインを投げるか

- **問い**: ワザ・効果の要素が、相手の「ダメージ・効果を受けない」「とうめい」などではたらかないと分かっているとき、その要素のコインを投げるか
- **規約の文（案）**: はたらかないことがコインの前に分かっている要素のコインも、説明どおりに投げる（乱数を使う）。結果はその要素に使わない。ほかの要素の処理は変えない
- **適用条件**: 要素のコインの前に、その要素の効果が無効（受けない・とうめい・［KEEP］など）と分かっていて、投げるかで乱数の列・ログが変わる場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_EVADED_EFFECT_COIN`（unverified）、`UNRESOLVED_PREVENTED_COIN_DAMAGE`（unverified）、`UNRESOLVED_PREVENTED_EFFECT_COIN`（unverified）、`UNRESOLVED_DISCARD_PROTECTED_COIN`（unverified）、`UNRESOLVED_KEEP_VOIDED_DISCARD_COIN`（unverified）
- **除外・対象外の隣の場面**: 対象の選び方の問い（KP1・LO1。個別）／ダメージのない要素のあとの効果（Z23。個別）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は投げて続ける
- **影響**: 公開の情報 コインの結果は公開／乱数 乱数の列がずれる（投げない案でもずれる。どちらでも規約集合の識別で比べ分ける）／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 要素のコインの共通の部品に規約の照会を加える
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 無効の盤面でのコイン・ログ・乱数の消費／無効でない盤面が今と同じ／厳密では今と同じ
- **推奨（案）**: 投げる（説明の手順のとおりで、要素ごとの「はたらかない」の判定をコインの前に読む必要がない）
- **代替案**: 投げない（結果を使わないコインを省く読み方）
- **根拠**: kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT（3 コード）。研究の記録: 裁定 AP1・HC3・KP2・L13・L5・T19b、kyuura の論点 UQ-COIN-IN-NULLIFIED-ELEMENT
- **未確認**: AP1・KP2 が同じ問いの型か（停止の文から当てた）
- **判断事項**: DEC-NULLIFIED-COINS（状態 proposal）

#### PC-ORDER-ATTACK-PRECHECK: ワザのダメージの前の複数のコインの順番

- **問い**: ワザを使うとき、ダメージの前に投げる複数のコイン（こんらん・ベイビィポケモンのルール・相手のとうめい・ジムなど）の順番
- **規約の文（案）**: ワザを使うとき、ダメージの前に投げる複数のコインは、ワザを使うプレイヤー（番のプレイヤー）が順番を選ぶ（決定を出す）。順番によらず結果の組が同じなら決定を出さない（今のまま）
- **適用条件**: ワザの宣言からダメージまでのあいだに、2 つ以上のコインの処理があり、順番で結果が変わる場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_ATTACK_CHECK_CONFUSION`（unverified）、`UNRESOLVED_BABY_RULE_COIN_ORDER`（unverified）、`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`（unverified）、`UNRESOLVED_VERMILION_GYM_ATTACK_ORDER`（unverified）、`UNRESOLVED_TRANSPARENCY_COIN_ORDER`（unverified）、`UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER`（unverified）、`UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER`（unverified）
- **除外・対象外の隣の場面**: ポケモンチェックの中（PC-CHECK-SIDE-ORDER）／錯乱ジムとちえくらべ（MG1。利用者の指定 USER-MIND-GAMES-OPTIONAL-BEFORE-COST の範囲の判断が先。個別）
- **依存・関係・競合**: 依存 なし／関係 PC-ORDER-OVERLAP／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は決定を出して続ける
- **影響**: 公開の情報 コインは公開／乱数 どのコインが乱数のどの値になるかが、選んだ順番で決まる／コスト なし／処理の順番 決定が増える
- **共通処理で実装できる範囲**: 順番の決定（並びを選ぶ決定）を共通の部品にする。v0.140 の prize_first と同じ形の決定
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 2 つのコインがある盤面で、決定・答えごとの結果／順番によらない盤面が今と同じ（決定が出ない）／厳密では今と同じ
- **推奨（案）**: 番のプレイヤーが選ぶ（ワザの手順は番のプレイヤーが進める。p.325 の「番のプレイヤーが決める」に近い）
- **代替案**: p.309 の手順の番号順・同じ番号なら説明の順（決定を増やさないが、手順の番号で分からないものが残る）
- **根拠**: kyuura の UQ-ATTACK-PRE-DAMAGE-COIN-ORDER（4 コード）・UQ-TRANSPARENCY-COIN-ORDER（2 コード）。研究の記録: 裁定 AC13・AC6・BQ1・NT1・T27・TS1・VM1、kyuura の論点 UQ-ATTACK-PRE-DAMAGE-COIN-ORDER・UQ-REACTIVE-SWITCH-DURING-ATTACK・UQ-TRANSPARENCY-COIN-ORDER
- **未確認**: NT1 が同じ型か（停止の文から当てた）
- **判断事項**: DEC-ORDER-RULE（状態 proposal）

#### PC-ORDER-OVERLAP: 同じ時点にはたらく複数の効果の当てはめの順番

- **問い**: 同じ時点にはたらく 2 つ以上の効果（ダメージを防ぐ・きぜつを防ぐ・持続する効果・特殊状態の上書き・反応など）を、どの順番で当てはめるか
- **規約の文（案）**: 同じ時点にはたらく複数の効果の順番で結果が変わるときは、その時点の番のプレイヤーが順番を選ぶ（決定を出す）。順番によらず結果が同じなら決定を出さない（今のまま）
- **適用条件**: ワザ・トレーナー・特殊能力の処理の中で、同時の効果が 2 つ以上あり、順番で結果が変わる場面（対象の一覧のコード）。ポケモンチェックは除く
- **対象の場面（続けられ方）**: `UNRESOLVED_DAMAGE_GUARD_OVERLAP`（unverified）、`UNRESOLVED_REFLECT_SHIELD_OVERLAP`（unverified）、`UNRESOLVED_TIME_TRAVEL_OVERLAP`（unverified）、`UNRESOLVED_KO_PREVENTION_ORDER`（unverified）、`UNRESOLVED_KO_SURVIVAL_OVERLAP`（unverified）、`UNRESOLVED_KOGA_POISON_ORDER`（unverified）、`UNRESOLVED_SPECIAL_POISON_OVERWRITE`（unverified）、`UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS`（unverified）、`UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER`（unverified）、`UNRESOLVED_GROUP_POWER_COIN_ORDER`（unverified）
- **除外・対象外の隣の場面**: ポケモンチェック（PC-CHECK-SIDE-ORDER）／ワザのダメージの前のコイン（PC-ORDER-ATTACK-PRECHECK）／効果の種類の優先（色のマーカー CM1・色の置きかえ CE2・最大HP の MH2・どくの量の合わせ方 PO1・鋼エネルギーと特殊能力 MT1）: 順番ではなく、どの効果が勝つかの読み方（個別）
- **例外**: サイドを取る順番は利用者の指定のまま（この規約に入れない）
- **依存・関係・競合**: 依存 なし／関係 PC-ORDER-ATTACK-PRECHECK／競合 PC-CHECK-SIDE-ORDER（ポケモンチェックには当てない）
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は決定を出して続ける
- **影響**: 公開の情報 決定の候補は公開の効果だけ／乱数 コインを含む効果は割り当てが変わる／コスト なし／処理の順番 決定が増える
- **共通処理で実装できる範囲**: PC-ORDER-ATTACK-PRECHECK と同じ順番の決定の部品
- **カード固有の対応が残る範囲**: 効果ごとの「同時」の判定は登録のまま
- **回帰テスト**: 2 つの効果がある盤面で、答えごとの結果／順番によらない盤面が今と同じ／厳密では今と同じ
- **推奨（案）**: 番のプレイヤーが選ぶ（p.325 の「同時に起こるときは番のプレイヤーが順番を決める」に近い（研究上の当てはめは未解決））
- **代替案**: 効果を受けるポケモンの持ち主が選ぶ（受ける側の効果の重なりでは自然だが、両方の側の効果が混ざると決まらない）
- **根拠**: 台帳の PF-SIMULTANEOUS-ORDER の候補 P-SO-1〜3。研究の記録: 裁定 15・C34・C35・DR18・G16・G40・GO1・KG1・KS2・P32・RF1・S7・TP3・TW2・XP1・Z18、kyuura の論点 UQ-KO-PREVENTION-ORDER・UQ-MULTIPLE-DAMAGE-TRIGGERS-ONE-ATTACK・UQ-POISON-OVERWRITE-ORDER・UQ-POST-KO-POWERS-ORDER
- **未確認**: 対象の 10 コードが同じ型か（停止の文・裁定の記録の行から当てた。コードごとに確かめていない）
- **判断事項**: DEC-ORDER-RULE（状態 proposal）

#### PC-SUPPRESSION-LATER-POKEMON: 特殊能力を消す効果は、あとから場に出たポケモンにも及ぶか

- **問い**: まきちらせ!ベトベトガス・やみのはどう・ふしぎなガスなど、特殊能力を消す効果がはたらいているあいだに場に出たポケモンの特殊能力も消えるか
- **規約の文（案）**: 特殊能力を消す効果は、はたらいているあいだ、そのとき場にいるすべての対象に及ぶ（効果がはたらきはじめたあとに場に出たポケモンを含む）
- **適用条件**: 特殊能力を消す効果がはたらいているあいだに、特殊能力を持つカードを場に出す・進化させる場面（GG1・DW1・ふしぎなガス）
- **対象の場面（続けられ方）**: `UNRESOLVED_GOOP_GAS_NEW_POKEMON`（unverified）、`UNRESOLVED_DARK_WAVE_NEW_POKEMON`（unverified）、`UNRESOLVED_STRANGE_GAS_NEW_POKEMON`（unverified）
- **除外・対象外の隣の場面**: 「特殊能力の効果を受けない」ポケモン（DW2・ふしぎなガスの MG2。個別）／消えていた特殊能力がもどる時点（SC2 など。個別）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は消えたまま出す
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 特殊能力の有効性の問い合わせ（共通）に規約の照会を加える
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 効果がはたらいているあいだに出したポケモンの特殊能力／効果がないときが今と同じ
- **推奨（案）**: 及ぶ（持続する効果を「はたらいているあいだの場」に当てはめる読み方（CR-POWER-BACK-AFTER-RECOVERY と同じ向き））
- **代替案**: はたらきはじめた時点の場のポケモンだけ（効果を一度だけ当てはめる読み方）
- **根拠**: effects.py の GG1・DW1 の理由の文／kyuura の UQ-GOOP-GAS-NEW-POKEMON。研究の記録: 裁定 DW1・GG1・MG1、kyuura の論点 UQ-GOOP-GAS-NEW-POKEMON
- **未確認**: 3 コードの止める条件が同じ型か
- **判断事項**: DEC-SUPPRESSION-READINGS（状態 proposal）

#### PC-NON-DAMAGE-HP-KNOCKOUT: ダメージ以外で HP がのっているダメージ以下になったポケモン

- **問い**: 進化・退化・最大HPを下げる効果など、ダメージ以外の原因で HP がのっているダメージ以下になったポケモンは、いつきぜつするか
- **規約の文（案）**: ダメージ以外の原因で HP がのっているダメージ以下になったポケモンは、その原因になったコマンドの処理の終わりにきぜつの判定をする（ポケモンチェックの 3・4 で起こったら、ポケモンチェックの終わりに判定する）
- **適用条件**: max_hp_drops が空でない・進化のあとに HP がダメージ以下（EVOLUTION_HP・DV1）
- **対象の場面（続けられ方）**: `UNRESOLVED_MAX_HP_DROP`（needs_implementation）、`UNRESOLVED_EVOLUTION_HP`（blocked_by_defect）、`UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT`（unverified）
- **除外・対象外の隣の場面**: 変身がもどるときのきぜつの時点（TK1。個別）／ワザのダメージによるきぜつ（今のまま）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否・HALTED。プレイ用はきぜつの判定をして続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 きぜつの判定の時点が増える
- **共通処理で実装できる範囲**: コマンドの終わり・ポケモンチェックの終わりに、きぜつの判定の窓を加える（今は MH1 で受け付けない・止める）
- **カード固有の対応が残る範囲**: なし
- **回帰テスト**: 最大HP が下がってきぜつする盤面（コマンド・ポケモンチェック・番の終わり）で、サイド・勝ち負け／厳密では今と同じ
- **推奨（案）**: 原因のコマンドの処理の終わりに判定（きぜつの判定の時点を新しく決める必要がある中で、いちばん近い既存の判定の時点）
- **代替案**: 次のワザ・ポケモンチェックのきぜつの判定まで待つ（HP 以上のダメージのポケモンが場に残る時間ができる）
- **根拠**: kyuura の UQ-EVOLUTION-HP-BELOW-DAMAGE（3 コード）／engine.py の max_hp_drops の分岐・procedures.py の _recovery_stop。研究の記録: 裁定 DV1・MH1、kyuura の論点 UQ-EVOLUTION-HP-BELOW-DAMAGE
- **未確認**: 判定の窓を加える実装の量
- **判断事項**: DEC-KNOCKOUT-READINGS（状態 proposal）

#### PC-REACTION-DOUBLE-KNOCKOUT: ワザのダメージと反応のダメージによる両方のきぜつ

- **問い**: ワザのダメージで相手がきぜつし、同じワザの処理の中の反応（返すダメージ・カウンター・みちづれ）でワザを使ったポケモンもきぜつするとき、同時のきぜつか
- **規約の文（案）**: 同じワザの処理の中のダメージと、そのダメージへの反応のダメージで両方のプレイヤーのポケモンがきぜつしたら、同時のきぜつとして扱う（サイドを取る順番は利用者の指定 USER-PRIZE-ORDER-* のまま）
- **適用条件**: ワザのダメージで相手の対戦ポケモンがきぜつしうるうえ、反応のダメージでワザを使ったポケモンもきぜつしうる場面（W24・C18・HC2）
- **対象の場面（続けられ方）**: `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`（unverified）、`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`（unverified）、`UNRESOLVED_DESTINY_BOND_KNOCKOUT`（unverified）
- **除外・対象外の隣の場面**: ポケモンチェックの両方のきぜつ（PC-CHECK-DOUBLE-KNOCKOUT）／反応の効果がきぜつしたポケモンからはたらくか（KD1。PC-TARGET-LOST-MID-EFFECT）
- **依存・関係・競合**: 依存 なし／関係 CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN・CONV:USER-PRIZE-ORDER-PER-PLAYER／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は同時のきぜつとして続ける
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 勝ち負け・サドン・デスへの移り方が変わる
- **共通処理で実装できる範囲**: ワザのあとのきぜつの処理（同時のきぜつの並びは v0.139・v0.140 で作った）に、反応のダメージのきぜつを同じ並びに入れる規約の照会を加える
- **カード固有の対応が残る範囲**: 反応の登録ごとに、ダメージの時点がワザの処理の中か
- **回帰テスト**: 両方がきぜつする盤面で、サイドの決定（prize_first）・勝ち負け・サドン・デス／片方だけのきぜつが今と同じ／厳密では今と同じ
- **推奨（案）**: 同時のきぜつ（同じワザの処理の中のきぜつは、ワザのあとのきぜつの判定でまとめて処理する（p.323））
- **代替案**: 反応のダメージのきぜつが後（反応の時点を後に読む読み方。勝ち負けが変わる）
- **根拠**: kyuura の UQ-RETALIATION-DOUBLE-KO・UQ-COUNTERATTACK-DOUBLE-KO・UQ-DESTINY-BOND-KO。研究の記録: 裁定 C18・HC2・S37・W24・Z13、kyuura の論点 UQ-COUNTERATTACK-DOUBLE-KO・UQ-DESTINY-BOND-KO・UQ-RETALIATION-DOUBLE-KO
- **未確認**: 3 つの反応のダメージの時点
- **判断事項**: DEC-KNOCKOUT-READINGS（状態 proposal）

#### PC-TARGET-LOST-MID-EFFECT: 効果の途中で対象・発生源がいなくなったとき

- **問い**: 効果の処理の途中で、その効果の対象・発生源のポケモンが場をはなれた・きぜつした・条件を満たさなくなったとき、残りの処理をどうするか
- **規約の文（案）**: 効果の処理の途中で、その効果の対象・発生源のポケモンが場をはなれた（きぜつを含む）・条件を満たさなくなったら、そのポケモンに関する残りの処理は行わない。ほかの処理は続ける
- **適用条件**: 処理の途中の確かめで、対象・発生源の変化を理由に止める場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_RECALL_TARGET_CHANGED`（needs_implementation）、`UNRESOLVED_REACTION_CONDITION_CHANGED`（needs_implementation）、`UNRESOLVED_REACTION_AFTER_KNOCKOUT`（needs_implementation）、`UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON`（needs_implementation）
- **除外・対象外の隣の場面**: 最初から対象がない（PC-USE-WITHOUT-TARGET）／持続する効果の発生源の進化・退化（PC-LASTING-SOURCE-CHANGE）
- **例外**: エンジンの未対応のコード（UNSUPPORTED_ATTACK_SOURCE_LEFT_PLAY・UNSUPPORTED_SECRET_PLAN_LOST_TARGET・UNSUPPORTED_PURSUIT_DAMAGE_REACTION）は B（規約の対象にしない。同じ規約を前提にした実装の候補）
- **依存・関係・競合**: 依存 なし／関係 PC-LASTING-SOURCE-CHANGE／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は残りを飛ばして続ける
- **影響**: 公開の情報 なし／乱数 飛ばした処理のコインは投げない／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 反応・処理の継続の状態（台帳の PF-RUNTIME-CONTINUATION と同じ不足）が先に要る
- **カード固有の対応が残る範囲**: 効果ごとに「そのポケモンに関する処理」の範囲
- **回帰テスト**: 途中で対象が場をはなれる盤面で、残りの処理・ログ／厳密では今と同じ
- **推奨（案）**: そのポケモンに関する残りを行わない（対象のない処理を推測で別のポケモンに移さない）
- **代替案**: 効果全体を止めない（対象がいなくても残りの処理の結果を記録する）（処理の範囲が決まらない）
- **根拠**: 台帳の PF-REACTION-DURING-PROCESS・PF-COPY-TRANSFORM。研究の記録: 裁定 KD1・RA1・RA2・RC3、kyuura の論点 UQ-REACTIVE-SWITCH-DURING-ATTACK・UQ-RECALL-SCOPE
- **未確認**: 4 コードが同じ型か／継続の実装の量
- **判断事項**: DEC-REACTION-READINGS・DEC-COPY-SCOPE（状態 proposal）

#### PC-LASTING-SOURCE-CHANGE: 持続する効果の発生源が進化・退化・場をはなれたとき

- **問い**: 相手のポケモンに与えた持続する効果（にげられない・ワザを使えない・どくの量など）は、効果を与えたポケモンが進化・退化・場をはなれたら続くか
- **規約の文（案）**: 発生源のポケモンに結び付いた持続する効果は、発生源が場をはなれたら終わる。発生源の進化・退化では終わらない（同じポケモンとして続く）
- **適用条件**: 持続する効果の記録の発生源が進化・退化・場をはなれた場面で、続くかで結果が変わる（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_CLAMPING_JAW_SOURCE_DEVOLVED`（needs_implementation）、`UNRESOLVED_JAW_CLAMP_SOURCE_EVOLVED`（needs_implementation）、`UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED`（needs_implementation）、`UNRESOLVED_MEAN_LOOK_SOURCE_EVOLVED`（needs_implementation）、`UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED`（needs_implementation）、`UNRESOLVED_POISON_MIST_SOURCE`（needs_implementation）
- **除外・対象外の隣の場面**: 効果を受けたポケモンの側の変化（今のまま）／「自分の番に 1 回」の記録（PC-ONCE-PER-TURN-IDENTITY）
- **例外**: 説明に終わる条件が書かれている効果（今のまま）
- **依存・関係・競合**: 依存 なし／関係 PC-TARGET-LOST-MID-EFFECT／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は規約で続く・終わるを決める
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 持続する効果の記録の終わり方（共通の期限の処理）に規約の照会を加える。発生源の記録（前の番の記録）が要る場面がある
- **カード固有の対応が残る範囲**: 効果ごとの発生源の結び付き
- **回帰テスト**: 発生源が進化・退化・場をはなれた盤面で、効果が続く・終わる／厳密では今と同じ
- **推奨（案）**: 場をはなれたら終わる・進化・退化では続く（進化・退化は同じポケモン（p.316 の進化の扱い）で、場をはなれたら別のカード）
- **代替案**: 発生源によらず続く（効果を受けたポケモンの記録とみなす読み方）
- **根拠**: 台帳の PF-HISTORY-LASTING。研究の記録: 裁定 CJ1・JC1・JC2・ML2・PO3・SG1、kyuura の論点 UQ-ATTACK-LOCK-SOURCE-RETURNED
- **未確認**: 6 コードが同じ型か
- **判断事項**: DEC-LASTING-READINGS（状態 proposal）

#### PC-ONCE-PER-TURN-IDENTITY: 「番に 1 回」「その番に〜した」の記録は、入れかわり・もどりで続くか

- **問い**: スタジアムを入れかえた・トラッシュからもどした、ポケモンが退化したなど、カード・ポケモンが入れかわったとき、同じ番の「1 回」「その番に〜した」の記録は続くか
- **規約の文（案）**: 「自分の番に 1 回」の使用の記録と「その番に〜した」の記録は、同じ番のうちは、同じ名前のカード・同じポケモン（進化・退化を含む）に続く。入れかえ・もどりで使い直せない
- **適用条件**: 同じ番の中で、記録のあるカード・ポケモンが入れかわった・もどった・退化した場面（対象の一覧のコード）
- **対象の場面（続けられ方）**: `UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT`（needs_implementation）、`UNRESOLVED_STADIUM_REUSE_AFTER_RETURN`（needs_implementation）、`UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT`（needs_implementation）、`UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION`（needs_implementation）、`UNRESOLVED_EVOLVE_AFTER_DEVOLUTION`（blocked_by_defect）
- **除外・対象外の隣の場面**: ラッキースタジアムの「くりかえし」（LK1。個別）／エネルギーをつける回数（R13・BL1。個別）
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否。プレイ用は記録を続けて拒否する（使い直せない）
- **影響**: 公開の情報 なし／乱数 なし／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 番の記録の照会（共通の部品）に規約の照会を加える
- **カード固有の対応が残る範囲**: 記録を同じとみなす単位（同じ名前・同じポケモン）はカードの型ごと
- **回帰テスト**: 入れかえ・もどり・退化のあとの使用／厳密では今と同じ
- **推奨（案）**: 続く（使い直せない）（番ごとの制限を入れかえで外さない読み方。挙動は今の拒否に近い）
- **代替案**: 入れかわったら別のカードとして使える（カードの物の同一性で読む読み方）
- **根拠**: 台帳の PF-HISTORY-LASTING／kyuura の UQ-DEVOLUTION-SAME-TURN・UQ-FUCHSIA-GYM-ONCE-PER-TURN。研究の記録: 裁定 DV2・DV3・FG1・RS1・SX2、kyuura の論点 UQ-DEVOLUTION-SAME-TURN・UQ-FUCHSIA-GYM-ONCE-PER-TURN
- **未確認**: 5 コードが同じ型か
- **判断事項**: DEC-LASTING-READINGS（状態 proposal）

#### PC-COPIED-ATTACK-AS-OWN: 写したワザは、写したポケモンのワザとして説明のすべてを処理するか

- **問い**: ものまね・オウムがえし・バーチャルなど、ほかのポケモンのワザを使うとき、そのワザの使う条件・持続する効果・ワザ以外の説明をどこまで処理するか
- **規約の文（案）**: 写したワザは、写したポケモン（使うポケモン）のワザとして、そのワザの説明のすべて（使う条件・持続する効果・ワザの効果でないものを除く）を処理する
- **適用条件**: 写したワザの説明に、使う条件・持続する効果・ねむりのときだけの条件・1 回だけの条件などがあり、写したときの扱いで結果が変わる場面（kyuura の UQ-COPIED-ATTACK の 7 コード）
- **対象の場面（続けられ方）**: `UNRESOLVED_COPIED_ATTACK`（needs_implementation）、`UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS`（needs_implementation）、`UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT`（needs_implementation）、`UNRESOLVED_MIRROR_MOVE_NON_ATTACK`（needs_implementation）、`UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK`（needs_implementation）、`UNRESOLVED_VIRTUAL_ASLEEP_ONLY_ATTACK`（needs_implementation）、`UNRESOLVED_VIRTUAL_ONCE_ATTACK`（needs_implementation）
- **除外・対象外の隣の場面**: へんしん・ばける・すごいへんしん（カードの仕組みごとの別の問い。個別）／思い出す（RC1〜RC4。個別）
- **例外**: 写したワザの型をエンジンが実装していない場合（UNSUPPORTED_COPIED_ATTACK・UNSUPPORTED_MIRROR_MOVE_*。B）は、規約があっても止める
- **依存・関係・競合**: 依存 なし／関係 なし／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否
- **影響**: 公開の情報 なし／乱数 写したワザのコインを投げる／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: 写したワザの処理の型ごとの実装（台帳の PF-RUNTIME-COPY-GAPS）が先
- **カード固有の対応が残る範囲**: 写すワザの型ごと
- **回帰テスト**: 写したワザの条件・持続する効果の盤面／厳密では今と同じ
- **推奨（案）**: 写したポケモンのワザとして説明のすべてを処理（ワザの説明を使う側で読み直す読み方）
- **代替案**: ダメージとダメージの効果だけを処理（使う条件・持続する効果を写さない読み方）
- **根拠**: kyuura の UQ-COPIED-ATTACK。研究の記録: 裁定 HC9・MM1・MM2・OM1・OM2・SQ1・VA1、kyuura の論点 UQ-COPIED-ATTACK
- **未確認**: 実装の量
- **判断事項**: DEC-COPY-SCOPE（状態 proposal）

#### PC-FACE-UP-DECK: フラッシュでおもてになった山札のカード

- **問い**: フラッシュでおもてにした山札のカードが山札にあるあいだ、引く・見る・並べかえる・山札の上に置く・見えない場所へ移すときにどう扱うか
- **規約の文（案）**: おもての山札のカードは、山札にあるあいだはおもてのまま（両方に見える）。山札の上から見えない場所（手札・サイド）へ移すときは、移る時点でおもてだった情報だけを公開にし、移ったあとは移った先の公開の範囲にしたがう。並べかえ・山札の上に置くときは、おもてのカードの位置を公開のまま更新する
- **適用条件**: faceup.command_problem が FU2〜FU6 を返す場面
- **対象の場面（続けられ方）**: `UNRESOLVED_FACE_UP_DECK_CHECK`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#draw`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#quiz-precheck`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#decision-halt`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_LOOK_RETURN`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_MOVE`（needs_secret_review）、`UNRESOLVED_FACE_UP_DECK_PLACE_TOP`（needs_secret_review）
- **除外・対象外の隣の場面**: マチスの秘策のうらのカード（FD1・FD2。個別）／エンジンの未対応の経路（UNSUPPORTED_FACE_UP_DECK_PATH。B）
- **依存・関係・競合**: 依存 なし／関係 PC-STATED-COUNT-SHORT／競合 なし
- **厳密モードとの差**: 厳密は今のまま拒否（どの答えでも当たれば HALTED）
- **影響**: 公開の情報 公開の範囲そのものを決める規約。秘密への非依存を確かめ直す／乱数 なし／コスト なし／処理の順番 なし
- **共通処理で実装できる範囲**: faceup の止め方を規約の照会で外し、公開の範囲の更新を共通にする
- **カード固有の対応が残る範囲**: クイズ・性格判定・カードめくりゲームの正誤の確かめ（v0.135・v0.136）の扱い
- **回帰テスト**: twin_command_problems の対の比べ（両方の集合で）／観測の公開の範囲／厳密では今と同じ
- **推奨（案）**: おもてのまま・移る時点の公開だけを残す（公開の情報を増やさず、移ったあとの扱いを既存の領域の規則にそろえる）
- **代替案**: おもてのカードを引いたら公開のまま手札に残る（相手に見える手札）（手札に公開のカードの表現が要る）
- **根拠**: docs/flash-faceup-deck-v0.126.md 6 章／kyuura の UQ-FLASH-FACE-UP-DECK。研究の記録: 裁定 FU2・FU3・FU4・FU5・FU6、kyuura の論点 UQ-FLASH-FACE-UP-DECK
- **未確認**: 読み方ごとの公開の範囲（研究上の未解決）
- **判断事項**: DEC-FACE-UP-DECK（状態 proposal）
<!-- generated:plan-candidate-details end -->

### 5.3 共通化しない場面（個別の対応）

規約案の対象にしなかった A の場面は、場面ごとに理由を JSON の `individual_reason` に書きました。族ごとの数（生成）:

<!-- generated:plan-individual begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 族（台帳） | 個別の場面 | 共通化しない理由 |
|---|---:|---|
| PF-TEXT-READING | 34 | カード固有の説明の読み方（同じ言い回しの別のカードに広げない） |
| PF-COPY-TRANSFORM | 26 | へんしん・ばける・すごいへんしん・思い出す・スケッチなど、1 つのカードの仕組みの中の問い（同じ仕組みのコードはまとめて判断できるが、ほかのカードに広げない） |
| PF-EFFECT-TIMING | 14 | カード固有の効果の時点の読み方（ずらかる・おとしあな・はかいのはどう・時間の歪みなど） |
| PF-ENERGY-TYPE | 10 | 色を変える効果・きせきのかぜ・エナジーバーンなど、カード固有のエネルギーの読み方 |
| PF-DAMAGE-SCOPE | 10 | カード固有のダメージの範囲・計算の読み方（ダメージの量を変える効果の当てはめの問いではない） |
| PF-HISTORY-LASTING | 9 | カード固有の記録・持続する効果の読み方 |
| PF-POWER-SUPPRESSION | 8 | 「特殊能力の効果を受けない」ポケモン・循環・消えた特殊能力の扱いなど、カード固有の問い |
| PF-REACTION-DURING-PROCESS | 7 | 途中の反応を使えるか（継続の実装と組）のカード固有の問い |
| PF-PROTECTED-TARGET-EFFECT | 7 | 対象の選び方・ダメージのない要素のあとの効果の読み方（コインの問いではない） |
| PF-KNOCKOUT-TIMING | 7 | カード固有のきぜつの時点の読み方（きあいのハチマキ・こんじょう・ふしちょう・変身のもどり・山札にもどす効果など） |
| PF-USE-WITHOUT-EFFECT | 7 | カード固有の読み方（使う条件・自分自身を選べるか・範囲の読み方など）。対象の有無だけの問いではない |
| PF-SIMULTANEOUS-ORDER | 6 | 効果の種類の優先（どの効果が勝つか）の読み方、または利用者の指定の範囲の判断が先の問い。順番を選ぶ規約では扱えない |
| PF-ESP-REDO | 4 | ナツメの ESP（1 枚のカードの仕組み）の問い |
| PF-SETUP-PLAY-AS-POKEMON | 3 | 準備の外の化石・人形の問い（にげる PF2・育て屋 PF3・ちえくらべ MG2）。カードごとの読み方 |
| PF-HIDDEN-INFORMATION | 3 | マチスの秘策のうらのカード・ヒートプレートの読み方（カード固有。秘密への非依存の確かめ直しが要る） |
<!-- generated:plan-individual end -->

個別の場面のうち、道具の対戦（6 章）で多く当たったもの（生成）:

<!-- generated:plan-individual-observed begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 場面 | 族 | 終端の局 | 拒否（回・局） | 個別の理由 |
|---|---|---:|---|---|
| `UNRESOLVED_POISON_MIST_EARLIER_POISON` | PF-HISTORY-LASTING | 11 | 0・0 | カード固有の記録・持続する効果の読み方 |
| `UNRESOLVED_POISON_CHANGE_ORDER` | PF-SIMULTANEOUS-ORDER | 1 | 0・0 | 効果の種類の優先（どの効果が勝つか）の読み方、または利用者の指定の範囲の判断が先の問い。順番を選ぶ規約では扱えない |
| `UNRESOLVED_EXTRA_ENERGY_COLORLESS` | PF-ENERGY-TYPE | 0 | 258・111 | 色を変える効果・きせきのかぜ・エナジーバーンなど、カード固有のエネルギーの読み方 |
| `UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT` | PF-KNOCKOUT-TIMING | 0 | 398・95 | カード固有のきぜつの時点の読み方（きあいのハチマキ・こんじょう・ふしちょう・変身のもどり・山札にもどす効果など） |
| `UNRESOLVED_PLAY_AS_POKEMON_RETREAT` | PF-SETUP-PLAY-AS-POKEMON | 0 | 93・91 | 準備の外の化石・人形の問い（にげる PF2・育て屋 PF3・ちえくらべ MG2）。カードごとの読み方 |
| `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE` | PF-PROTECTED-TARGET-EFFECT | 0 | 122・33 | 対象の選び方・ダメージのない要素のあとの効果の読み方（コインの問いではない） |
| `UNRESOLVED_FOCUS_BAND_TIMING` | PF-KNOCKOUT-TIMING | 0 | 221・29 | カード固有のきぜつの時点の読み方（きあいのハチマキ・こんじょう・ふしちょう・変身のもどり・山札にもどす効果など） |
| `UNRESOLVED_LEGEND_BODY_TRAINER_TARGET` | PF-TEXT-READING | 0 | 634・28 | カード固有の説明の読み方（同じ言い回しの別のカードに広げない） |
| `UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT` | PF-USE-WITHOUT-EFFECT | 0 | 79・26 | ポケモンタワーで効果がすべて消えるときに使えるか（カード固有の読み方。対象の有無の問いではない） |
| `UNRESOLVED_TRANSFORM_ENERGY_COUNT` | PF-COPY-TRANSFORM | 0 | 145・24 | へんしん・ばける・すごいへんしん・思い出す・スケッチなど、1 つのカードの仕組みの中の問い（同じ仕組みのコードはまとめて判断できるが、ほかのカードに広げない） |
| `UNRESOLVED_OPPONENT_POKEMON_COUNTERS` | PF-TEXT-READING | 0 | 96・22 | カード固有の説明の読み方（同じ言い回しの別のカードに広げない） |
| `UNRESOLVED_RETREAT_REACTION_TIMING` | PF-EFFECT-TIMING | 0 | 34・20 | カード固有の効果の時点の読み方（ずらかる・おとしあな・はかいのはどう・時間の歪みなど） |
<!-- generated:plan-individual-observed end -->

個別でも、終端を起こすもの・多くの局で当たるものは、共通規約を待たずに、1 枚のカード・1 つの仕組みの判断として先に決める候補です（9 章）。

族は台帳の書式の単位で、採用の単位ではありません。同じ族でも、文面・情報の条件・時点が違う場面は共通化していません。例えば次のものです。

- PF-TEXT-READING（説明の読み方）は、同じ言い回しでも別のカードの記録が別の問いとして扱うので、共通化していません。
- PF-COPY-TRANSFORM のうち、へんしん・ばける・すごいへんしん・思い出すは、それぞれ 1 つのカードの仕組みの中の問いです。kyuura の論点（UQ-SHAPESHIFT-SCOPE・UQ-RECALL-SCOPE・
  UQ-TRANSFORM-SCOPE）ごとにまとめて判断できますが、ほかのカードに広げる共通規約にはしていません。

## 6. 実際の発生の記録（道具の対戦）

停止コードの件数から、対戦の停止率を推定していません。次は、今の木で流し直した道具の対戦の数え上げです（記録はリポジトリの外の
`C:/dev/kyuura-engine-play-policy-evidence/`。sha256 は同じ場所の `MANIFEST.md`）。停止の方針の台帳の作成スクリプトは `C:/dev/kyuura-engine-verification` の下の
記録をすべて到達可能性の証拠として読むので、この記録はその外に置きました。中に置くと、台帳の到達可能性が黙って変わります（台帳の更新は別の作業。10 章）。

<!-- generated:plan-observation begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
- 木: `8164194ca289c5f7f332c7f16d7f700a81a37215`（版 0.141.0）。道具: tools/existing_effect_games.py（全 108 バッチ。--start 0 --seeds 4）。方策: 各バッチの道具の方策（合法なコマンドだけを送る。拒否されたら別の操作を選ぶ。v0.140 から prize_first には番のプレイヤー）。seed: 0〜3（組ごと・席ごと）。組: 108 バッチ（各バッチの組 × 2 席 × seed）
- 分母: 対戦 4356 局。数え方: 1 局の終わり方（game_over・halted・道具の打ち切り）を 1 回ずつ。拒否は局ごとの回数の合計（同じ局の同じ拒否を重ねて数える）

| 終わり方 | 局 | 意味 |
|---|---:|---|
| game_over | 4233 | 通常の終わり |
| halted | 102 | エンジンの HALTED（終端） |
| interrupted | 13 | 途中停止（終端） |
| sudden_death | 6 | サドン・デスに移った（この道具は延長戦を進めない。延長戦はサドン・デスの道具で別に数える） |
| unexpected_rejection | 2 | 道具が予期しない拒否で局を打ち切った（エンジンは拒否しただけで終端ではない。2 局とも MG1） |

| 終端のコード（HALTED・途中停止） | 局 | 規約案・区分 |
|---|---:|---|
| `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` | 37 | PC-CHECK-SIDE-ORDER |
| `UNRESOLVED_PLAY_AS_POKEMON_SETUP` | 28 | PC-SETUP-PLAY-AS-POKEMON（事例ごと） |
| `UNRESOLVED_MULLIGAN_COMPENSATION` | 17 | PC-SETUP-MULLIGAN-COUNT（事例ごと） |
| `UNRESOLVED_POISON_MIST_EARLIER_POISON` | 11 | A（個別） |
| `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT` | 9 | PC-COIN-COUNT-SHORT |
| `UNRESOLVED_POISON_MIST_SOURCE` | 7 | PC-LASTING-SOURCE-CHANGE |
| `UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT` | 4 | PC-COIN-COUNT-SHORT |
| `UNRESOLVED_POISON_CHANGE_ORDER` | 1 | A（個別） |
| `UNSUPPORTED_TRANSFORM_COPIED_POWER` | 1 | B（規約の対象外） |

| 拒否（回数の多い順。上位 25。対戦は止まらず、道具は別の操作を選んだ） | 回 | 局 | 規約案・区分 |
|---|---:|---:|---|
| `UNRESOLVED_LEGEND_BODY_TRAINER_TARGET` | 634 | 28 | A（個別） |
| `UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT` | 398 | 95 | A（個別） |
| `UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET` | 272 | 15 | A（個別） |
| `UNRESOLVED_EXTRA_ENERGY_COLORLESS` | 258 | 111 | A（個別） |
| `UNRESOLVED_PREVENTED_EFFECT_COIN` | 221 | 91 | PC-NULLIFIED-ELEMENT-COIN |
| `UNRESOLVED_FOCUS_BAND_TIMING` | 221 | 29 | A（個別） |
| `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` | 219 | 85 | PC-NON-ATTACK-DAMAGE-MODIFIERS |
| `UNRESOLVED_EVADED_EFFECT_COIN` | 213 | 42 | PC-NULLIFIED-ELEMENT-COIN |
| `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` | 211 | 27 | PC-REACTION-DOUBLE-KNOCKOUT |
| `UNRESOLVED_PREVENTED_COIN_DAMAGE` | 168 | 67 | PC-NULLIFIED-ELEMENT-COIN |
| `UNRESOLVED_COPIED_ATTACK` | 155 | 27 | PC-COPIED-ATTACK-AS-OWN |
| `UNRESOLVED_TRANSFORM_ENERGY_COUNT` | 145 | 24 | A（個別） |
| `UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE` | 135 | 32 | PC-FACE-UP-DECK（事例ごと） |
| `UNRESOLVED_EFFECT_AFTER_NO_DAMAGE` | 122 | 33 | A（個別） |
| `UNRESOLVED_RETREAT_OVERPAY` | 100 | 49 | PC-RETREAT-COST-PAYMENT |
| `UNRESOLVED_OPPONENT_POKEMON_COUNTERS` | 96 | 22 | A（個別） |
| `UNRESOLVED_PLAY_AS_POKEMON_RETREAT` | 93 | 91 | A（個別） |
| `UNRESOLVED_STATED_CARDS_SHORT` | 90 | 19 | PC-HIDDEN-SEARCH-EMPTY・PC-STATED-COUNT-SHORT（事例ごと） |
| `UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT` | 79 | 26 | A（個別） |
| `UNRESOLVED_RAINBOW_ENERGY_TYPE` | 71 | 20 | PC-SPECIAL-ENERGY-CARD-WORDING |
| `UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE` | 63 | 24 | PC-UNSTATED-WEAKNESS-RESISTANCE |
| `UNRESOLVED_EVOLVE_AFTER_DEVOLUTION` | 58 | 26 | PC-ONCE-PER-TURN-IDENTITY |
| `UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE` | 57 | 10 | A（個別） |
| `UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER` | 56 | 10 | PC-ORDER-ATTACK-PRECHECK |
| `UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS` | 54 | 33 | PC-COPIED-ATTACK-AS-OWN |

- サドン・デスの道具（tools/sudden_death_games.py。corpus magnemite・swap・seed 0〜199）: 対戦 400 局、終わり方 {'game_over': 400}、延長戦の開始 21 回、延長戦の準備の HALTED なし
<!-- generated:plan-observation end -->

- 道具の方策は合法なコマンドだけを送り、拒否されたら別の操作を選びます。拒否の数は「道具が試した回数」で、実際の対戦で選びたい操作の数ではありません。
- 組・デッキは各バッチの検証用デッキ（公開の固定デッキではない）で、ふだんの対戦の分布を表しません。0 回のコードを到達しないとは読みません。

## 7. この調査で見つけた共通の不具合（修正していない）

`PSP-NJ1-NINJA-GYM-ORACLE`（確認済みの漏れ。構築盤面）:

- キョウの忍者ジム（PR1-067）の使う前の確かめ（`CoinBenchOwnerBasicFromDeckStadium.check_activation`。`effects.py:21276`〜`21281`）は、山札の実際の中身（`deck_cards_matching`）で
  NJ1 を判定します。
- 比較プローブで、プレイヤー 0 から見て公開の情報が同じ 2 盤面を作りました。キョウのアーボ（PMCG6-002）を山札の 11 枚目に置く盤面と、サイドの 1 枚目に置く盤面です。
  前者では `UseStadium(0)` を受理し、後者では `UNRESOLVED_NINJA_GYM_WITHOUT_TARGET` で拒否しました。`twin_command_problems` が段 0 で検出しました。
- v0.137 の PSP-ST1-DECK-ORACLE と同じ型（受理・拒否による漏れ）です。v0.136 の横断は `check_playable`・`check_usable` だけでした。今回、`check_activation` などのほかの `check*` を
  同じ型で探し、山札を読むのはこの 1 つでした（エネルギースタジアムはトラッシュを読むので公開）。
- 修正・停止の方針の台帳への追加はしていません。判断の材料は DEC-INFO-LEAK-FIXES です。規約案 `PC-USE-WITHOUT-TARGET` では、この場面を `blocked_by_defect` にしました。

規約案の対象のうち、ほかに未修正・未確認の不具合がある場面（`blocked_by_defect`）は、JSON の `defect_coupling` にあります。PSP-INCREASE-ENTRY-PW3-ORACLE（PW3）・
PSP-COCOON-DV2-ORACLE（DV2）・PSP-DECK-CONTENT-PRECHECKS の残り（GV1・EVOLUTION_HP）です。プレイ用の規約で不具合を覆いません。

## 8. 推奨する採用・実装の順序（案）

### 8.1 優先の観点ごとの表（生成）

観点は、対戦全体を止めるか・実際の発生・場面とコードの広さ・ほかの規約の前提か・実装と検証の負担・情報と処理の順番の危険・規約を当てても別の停止が残るか、です。コード数だけで
効果を評価していません（HALTED の局数と拒否の回数は 6 章の道具の記録で、コードの単位。＊は、事例を分けたコードの数で、ほかの事例の分を含む）。

順の考え方（案）:

- **S2a を最初にします**。道具の対戦の終端（115 局）のうち 95 局は、両方のねむり・化石と人形の初手・切り直しの補償・途中停止の 2 つの 4 つの規約案の対象です。どれも規約だけで
  判断を当てられます（化石と人形・ねむりのあとには、既存の停止が残りうる）。
- 残りの終端は 20 局です。［ポイズンミスト］が 18 局（PO3 は S2b の `PC-LASTING-SOURCE-CHANGE` で一部、PO2 は個別）、PO1 が 1 局（個別）、写した特殊能力の B が 1 局です。
  PO2・PO3 は、共通規約とは別に、1 枚のカードの判断として先に決める候補です（9 章）。
- **拒否は対戦を止めません**。拒否の多い規約案（`PC-NULLIFIED-ELEMENT-COIN`・`PC-NON-ATTACK-DAMAGE-MODIFIERS`・`PC-REACTION-DOUBLE-KNOCKOUT` など）は、選べる操作を増やす効果です。
  終端の規約案の次に置きました。
- `PC-USE-WITHOUT-TARGET`・`PC-USE-WITHOUT-EFFECT`・`PC-UP-TO-ZERO` は、場面の数は多いですが、道具の記録の拒否は 0 回でした（0 回を到達しないとは読まない）。推奨案
  （今の拒否を規約にする）は挙動が変わらず、負担も小さいので、S1 の基盤の確かめに使えます。

<!-- generated:plan-priority begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 段階 | 規約案 | 全体停止 | 場面 | コード | HALTED の局 | 拒否（回・局） | 前提になる規約 | 負担 | 危険 | 別の停止・未確認の残る場面 |
|---|---|:---:|---:|---:|---:|---|---|---|---|---:|
| S2a | `PC-CHECK-SIDE-ORDER` | ○ | 3 | 3 | 37 | 0・0 | PC-CHECK-DOUBLE-KNOCKOUT | 小（2 か所の分岐） | 中（乱数の割り当て・先攻後攻の偏りを測る） | 3 |
| S2a | `PC-SETUP-MULLIGAN-COUNT` | ○ | 2 | 1 | 17＊ | 0・0＊ | — | 小（1 か所の分岐） | 小（公開・乱数の新しい消費なし） | 0 |
| S2a | `PC-SETUP-PLAY-AS-POKEMON` | ○ | 2 | 1 | 28＊ | 0・0＊ | — | 小（推奨案）・大（代替案） | 小 | 2 |
| S2a | `PC-COIN-COUNT-SHORT` | ○ | 2 | 2 | 13 | 0・0 | — | 小（共通のチェック地点） | 小 | 2 |
| S2a | `PC-CHECK-KO-POINT` | ○ | 1 | 1 | 0 | 0・0 | — | 小 | 中（勝ち負け） | 1 |
| S2b | `PC-NON-ATTACK-DAMAGE-MODIFIERS` | ○ | 10 | 10 | 0 | 219・85 | — | 中（量の問い合わせの部品） | 小（量だけ） | 10 |
| S2b | `PC-LASTING-SOURCE-CHANGE` | ○ | 6 | 6 | 7 | 0・0 | — | 中（発生源の記録） | 小 | 6 |
| S2b | `PC-NON-DAMAGE-HP-KNOCKOUT` | ○ | 3 | 3 | 0 | 49・14 | — | 中（判定の窓） | 中（勝ち負け） | 3 |
| S2b | `PC-CHECK-DOUBLE-KNOCKOUT` | ○ | 1 | 1 | 0 | 0・0 | — | 中（ポケモンチェックの続きの並び） | 中（勝ち負け・サドン・デス） | 1 |
| S3 | `PC-USE-WITHOUT-TARGET` |  | 38 | 38 | 0＊ | 0・0＊ | — | 小（拒否の記録だけ） | 小（今と同じ。止める条件が公開で決まることの確かめが要る） | 38 |
| S3 | `PC-UP-TO-ZERO` |  | 13 | 13 | 0 | 0・0 | — | 小（答えの範囲の部品） | 小 | 13 |
| S3 | `PC-ORDER-OVERLAP` |  | 10 | 10 | 0 | 17・6 | — | 中 | 中 | 10 |
| S3 | `PC-STATED-COUNT-SHORT` |  | 9 | 9 | 0＊ | 109・29＊ | — | 中（効果の型ごとのあるだけの処理） | 小（枚数は公開） | 9 |
| S3 | `PC-SPECIAL-ENERGY-CARD-WORDING` |  | 9 | 9 | 0 | 111・39 | — | 中 | 小 | 9 |
| S3 | `PC-USE-WITHOUT-EFFECT` |  | 7 | 7 | 0 | 0・0 | PC-CHOOSE-TARGET-WITHOUT-EFFECT | 小 | 小 | 7 |
| S3 | `PC-ORDER-ATTACK-PRECHECK` |  | 7 | 7 | 0 | 77・18 | — | 中（順番の決定の部品） | 中（乱数の割り当て・決定の増加） | 7 |
| S3 | `PC-CHOOSE-TARGET-WITHOUT-EFFECT` |  | 5 | 5 | 0 | 0・0 | — | 小 | 小（候補を黙って減らさない記録） | 5 |
| S3 | `PC-NULLIFIED-ELEMENT-COIN` |  | 5 | 5 | 0 | 611・206 | — | 小 | 中（乱数の列） | 5 |
| S3 | `PC-ONCE-PER-TURN-IDENTITY` |  | 5 | 5 | 0 | 58・26 | — | 小 | 小 | 5 |
| S3 | `PC-SUPPRESSION-LATER-POKEMON` |  | 3 | 3 | 0 | 13・8 | — | 小 | 小 | 3 |
| S3 | `PC-REACTION-DOUBLE-KNOCKOUT` |  | 3 | 3 | 0 | 264・50 | — | 中 | 中（勝ち負け） | 3 |
| S3 | `PC-UNSTATED-WEAKNESS-RESISTANCE` |  | 2 | 2 | 0 | 63・24 | — | 小 | 小 | 2 |
| S3 | `PC-RETREAT-COST-PAYMENT` |  | 2 | 2 | 0 | 104・50 | — | 小 | 小 | 2 |
| S4 | `PC-FACE-UP-DECK` | ○ | 7 | 5 | 0＊ | 135・32＊ | — | 大 | 大（公開の範囲そのもの） | 7 |
| S4 | `PC-COPIED-ATTACK-AS-OWN` |  | 7 | 7 | 0 | 220・67 | — | 大（型ごとの実装） | 中 | 7 |
| S4 | `PC-HIDDEN-SEARCH-EMPTY` |  | 4 | 4 | 0＊ | 90・19＊ | — | 中（見つからない処理） | 大（秘密への非依存） | 4 |
| S4 | `PC-TARGET-LOST-MID-EFFECT` |  | 4 | 4 | 0 | 0・0 | — | 大（継続の状態） | 中 | 4 |
<!-- generated:plan-priority end -->

### 8.2 実装の段階（生成）

<!-- generated:plan-stages begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->
| 段階 | 名前 | 規約案 | 先に要るもの | 共通処理の変更の範囲 | 完了の基準 | 残るもの |
|---|---|---|---|---|---|---|
| S0 | 両モード共通の不具合の修正（モードと別の版） | — | — | PSP-NJ1-NINJA-GYM-ORACLE（この調査で確認）・PSP-INCREASE-ENTRY-PW3-ORACLE・PSP-COCOON-DV2-ORACLE・PSP-DECK-CONTENT-PRECHECKS の残り（未確認） | 対の比べ（twin_command_problems）で漏れがない。blocked_by_defect の場面の規約を採れる状態 | 研究上の論点（NJ1・PW3・DV2・GV1 の裁定）は未解決のまま |
| S1 | 規約集合を受け取る基盤と、今の挙動の保持 | — | DEC-RULESET-IDENTITY・DEC-RULESET-VERSIONING・DEC-CONVENTION-GRANULARITY・DEC-CONVENTION-CONFLICTS・DEC-MODE-CHANGE-DURING-GAME・DEC-LEGACY-STATES・DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS | 規約集合を new_game で受け取り状態に持つ（延長戦は keep）・止める箇所に事例の識別（場面 ID）・規約の照会の入口（登録の側。engine.py・resolution/ にカード ID・モード名の分岐を加えない）・規約による拒否と未決の裁定の停止を区別する記録・構成の検査（ruleset-mode-design.md 6.4 節）・厳密と厳密の比べ | 厳密の集合（基礎集合だけ）で、全体テスト・lockstep・前の版の組・サドン・デスの比べが今と同じ（意図した差 0）。規約の照会がどの場面でも「規約なし」を返し、止め方が今のまま | 続行規約は 1 つも入っていない。保存形式・識別の形は判断のあとに決める（この設計では決めない） |
| S2a | 対戦全体を止める規約（規約だけで足りるもの） | PC-SETUP-MULLIGAN-COUNT・PC-SETUP-PLAY-AS-POKEMON・PC-CHECK-SIDE-ORDER・PC-COIN-COUNT-SHORT・PC-CHECK-KO-POINT | S1・DEC-PLAY-CONFIG-INCOMPLETE-START | 準備・ポケモンチェック・途中停止の HALTED の分岐を、規約の照会で続行に置きかえる | 規約ごとに、当たる盤面の結果（状態・乱数・ログ・観測）・隣の場面が変わらないこと・厳密との差が規約の当たった歩から始まること・道具の対戦で HALTED の減り方と先攻後攻の偏り | WG-CHECK-PLAN・WG-CHECK-RECOVERY・WG-DECISION-NO-ANSWER のカード固有の停止、技術的な上限（くろこげマーカー・きのみ） |
| S2b | 対戦全体を止める規約（実装が要るもの） | PC-CHECK-DOUBLE-KNOCKOUT・PC-NON-DAMAGE-HP-KNOCKOUT・PC-NON-ATTACK-DAMAGE-MODIFIERS・PC-LASTING-SOURCE-CHANGE | S2a | ポケモンチェックの続きの両方のサイド・交代の並び、ダメージ以外の HP 低下のきぜつの判定の窓、ワザ以外のダメージの量の問い合わせ | S2a と同じ。両方のきぜつ・サドン・デスへの移り方の比べ | カード固有の時点の問い（SC1・SC2・AL1・AL3・MEW1 など） |
| S3 | 多数のカードに共通する通常の操作の規約 | PC-USE-WITHOUT-TARGET・PC-USE-WITHOUT-EFFECT・PC-CHOOSE-TARGET-WITHOUT-EFFECT・PC-UP-TO-ZERO・PC-STATED-COUNT-SHORT・PC-UNSTATED-WEAKNESS-RESISTANCE・PC-SPECIAL-ENERGY-CARD-WORDING・PC-RETREAT-COST-PAYMENT・PC-NULLIFIED-ELEMENT-COIN・PC-ORDER-ATTACK-PRECHECK・PC-ORDER-OVERLAP・PC-SUPPRESSION-LATER-POKEMON・PC-REACTION-DOUBLE-KNOCKOUT・PC-ONCE-PER-TURN-IDENTITY | S1 | 使う前・答えの確かめの拒否を、規約の照会で規約による拒否・受け付けに置きかえる。順番の決定の共通の部品 | 規約ごとの回帰（当たる盤面・隣の場面・対の比べ・厳密との差）。対象の一覧の場面ごとに、止める条件が規約の適用条件と同じことをコードで確かめる（unverified を解消する） | 個別の場面（カード固有の読み方） |
| S4 | 特殊な相互作用の規約（秘密の確かめ・実装が要るもの） | PC-HIDDEN-SEARCH-EMPTY・PC-FACE-UP-DECK・PC-TARGET-LOST-MID-EFFECT・PC-COPIED-ATTACK-AS-OWN | S1・S0 | 探して見つからない処理・おもての山札の公開の範囲・継続の状態・写したワザの型ごとの実装 | 両方の集合での対の比べ・継続の状態の保存と再生 | B の実装の不足（PF-RUNTIME-*） |
<!-- generated:plan-stages end -->

設計の原則（[ruleset-mode-design.md](ruleset-mode-design.md) をそのまま使う）:

- 同じ処理基盤に規約集合を渡します。止める箇所ごとに、場面の識別（台帳の場面 ID）で規約集合を照会します。
- 規約があり実装されていれば、その規約で続けます。規約がなければ、今と同じく止めます。
- 停止コードごとに例外を捕まえて続ける構造（catch-and-continue）にしません。例外を一括で無視する構造にもしません。
- 照会は登録の側に置きます。`engine.py`・`resolution/` にモード名・カード ID の分岐を加えません。
- 規約集合の ID・版・保存形式・切り替えの方法は決めていません（DEC-RULESET-IDENTITY・DEC-RULESET-VERSIONING・DEC-LEGACY-STATES ほか。S1 の前提）。
- 識別子の例（`PC-*`）は、設計案の中の名前です。API・保存の識別子として確定していません。

## 9. 利用者に判断してほしい事項

判断事項の本文（問い・選択肢・推奨・影響）は、置き場所の文書（[stop-policy-decisions.md](stop-policy-decisions.md)・[ruleset-mode-decisions.md](ruleset-mode-decisions.md)）に
あります。ここでは、この設計案で新しく加わった材料だけを書きます（同じ判断事項を 2 か所に書かない）。

1. **最初に判断する規約群（S2a）**: `PC-SETUP-MULLIGAN-COUNT`（DEC-MULLIGAN-COMPENSATION）・`PC-SETUP-PLAY-AS-POKEMON`（DEC-PLAY-AS-POKEMON）・`PC-CHECK-SIDE-ORDER`
   （DEC-SLEEP-COIN-ORDER・DEC-ORDER-RULE）・`PC-COIN-COUNT-SHORT`（DEC-STATED-COUNT-SHORT・DEC-DEFERRED-RESUME）・`PC-CHECK-KO-POINT`（DEC-KNOCKOUT-READINGS）。それぞれの推奨案と
   代替案は 5.2 節にあります。
2. **規約集合の基盤の判断（S1 の前提）**: DEC-RULESET-IDENTITY・DEC-RULESET-VERSIONING・DEC-CONVENTION-GRANULARITY・DEC-CONVENTION-CONFLICTS・DEC-MODE-CHANGE-DURING-GAME・DEC-LEGACY-STATES・
   DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS・DEC-PLAY-CONFIG-INCOMPLETE-START。
3. **利用者指定の範囲**: サイドを取る順番の利用者指定（USER-PRIZE-ORDER-ALWAYS-CHOSEN）を、ポケモンチェックの両方のきぜつに広げるか（`PC-CHECK-DOUBLE-KNOCKOUT` の代替案）。
   錯乱ジムとちえくらべ（MG1）は、USER-MIND-GAMES-OPTIONAL-BEFORE-COST の範囲の判断が先です（DEC-CHAOS-GYM-MIND-GAMES。順番の規約案の対象にしていない）。
4. **共通の不具合**: `PSP-NJ1-NINJA-GYM-ORACLE` を、ほかの漏れと同じくモード共通の不具合として直すか（DEC-INFO-LEAK-FIXES）。
5. **個別でも先に決める候補**: 道具の対戦で終端・多くの拒否を起こした個別の場面（5.3 節の生成した表）です。［ポイズンミスト］PO2・PO3 はポケモンチェックの HALTED で、
   DEC-LASTING-READINGS の材料です。拒否のあった局の多いものも候補です。EXTRA_ENERGY_COLORLESS・RETURN_IN_PLAY_TO_DECK_KNOCKOUT などで、族ごとの判断事項
   （stop-policy-decisions.md 4 章）の材料です。共通規約にしない理由は、場面ごとの `individual_reason` にあります。
6. **規約案を採る単位**: 規約案は、1 つの規約の文を、明示した場面の一覧に当てる形です（DEC-CONVENTION-GRANULARITY の事例単位の案と同じ）。承認は、規約の文と場面の一覧の両方に
   必要です。一覧の一部だけを承認することもできます。`unverified` の場面は、承認の前に止める条件をコードで確かめる作業（S3 の完了の基準）が要ります。

## 10. 未確認と設計の限界

- **続けられ方の多くは `unverified`** です。規約案の対象の場面の多くは、停止の文・裁定の記録の行・kyuura の論点の ID から当てたものです。止める条件が規約の適用条件と同じか、
  規約を当てた後に別の停止がないかを、場面ごとにコードで確かめたのは、対戦全体を止める論点（4 章）の一部だけです。
- **動的に HALTED に変わる経路**（4.1 節の WG-CHECK-RECOVERY・WG-TURN-END-SUPPRESSION・WG-DECISION-NO-ANSWER）は、どのコードが通るかの全件を特定していません。
  `form_problems` が返すコードは、静的に一部だけ確かめました。
- **事例の分割**: 台帳の事例（17）のほかに、同じコードで問い・公開の情報・処理の段階が違う場面がありうるかは、確かめていません。BY1（順番の問いに効果の種類の順番を含む）と、
  両方のきぜつ（問いが 3 つ）は、場面の中の複数の問いとして記録しました（`partial`）。台帳の事例は増やしていません。
- **研究の記録**: 公式資料の再調査・kyuura の固定コミットより後の記録の照合はしていません（台帳の RESEARCH-ALIGNMENT-NOT-LATEST のまま）。推奨案は、プレイ用の規約の案です。
  研究上の解決ではありません。
- **発生の記録**: 旧バッチの組・seed 0〜3・道具の方策の範囲だけです。先攻・後攻の偏り・勝率への影響は測っていません（規約ごとの検証の項目）。この記録では、台帳で
  `static_only`・`constructed_board` のコードにも、拒否・終端が観測されたものがあります。台帳の到達可能性（v0.134〜v0.136 の記録が根拠）は更新していません。更新するなら、
  台帳の証拠の作り直しとして別に行います。
- **規約案の数と範囲**: 個別の場面のうち、同じ kyuura の論点・同じカードの仕組みのものは、まとめて判断できる可能性があります（5.3 節）。この設計案では、共通規約として数えていません。
- **新しい漏れの横断**: `check*` の関数のうち、山札を読んで `UnsupportedError` を投げるものだけを AST で探しました。答えの候補・理由の文・決定の中の拒否の全件は見ていません
  （台帳 14 章の限界のまま）。

## 11. 検証

| 検証 | 内容 |
|---|---|
| 参照切れ | `--check`: 場面が台帳の現在有効な項目と一致する（対応先のない項目・台帳にない場面がない）。規約案の対象・依存・関係・判断事項・経路の場面と規約案が存在する |
| 対応先か対象外の理由 | `--check`: A の場面に規約案か個別の理由がある。A 以外は区分と理由がある（未分類がない） |
| 規約の対象に機能不足・安全上の停止が入っていない | `--check`: 規約案の対象はすべて A（研究の停止コード）。B・C・D・E の場面を対象にしない。未修正の不具合のある場面は `blocked_by_defect` |
| 集計の重複・適用条件と例外の欠け | `--check`: 1 つの場面に 2 つ以上の規約案が当たらない。規約案の必須の項目（問い・文・適用条件・除外・影響・推奨・代替・根拠・未確認）が空でない。範囲の分からない言い方の文がない。集計が場面から求めた値と同じ |
| 案と承認の区別 | `--check`: 規約案の状態は proposal だけ |
| 作り直しとの一致 | `--check`: 台帳とスクリプトから作り直した設計案と、書き出した設計案が同じ。この文書の生成した表が JSON と同じ |
| 壊した設計案を見つけること | `tests/test_play_policy_family_plan.py`（件数を期待値に写さない。わざと壊した設計案を `check` が見つけることを確かめる） |

### 11.1 実行した範囲（2026-11-04。全体の対戦テスト・全体のテストは流していない: エンジン・既存のテスト・データを変えていないため）

| 実行 | 結果 |
|---|---|
| `scripts/build_play_policy_family_plan.py --check` | 問題 0（終了コード 0） |
| `scripts/build_stop_policy_classification.py --check` | 基点 `8164194` の木（git archive の写し）で、作り直した台帳との違いを報告した（終了コード 1）。違いは v0.141 の拒否の文の変更で動いた行番号（`UNRESOLVED_RULING`・`UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`）と、v0.141 のテストの `UNSUPPORTED_DECISION` の記録だけ。`--write` で作り直し（別のコミット。項目・分類・集計は同じ）、そのあと問題 0 |
| `scripts/check_implementation_assumptions.py --check`・`scripts/check_normalization_revalidation.py --check` | どちらも問題 0（終了コード 0） |
| 設計案・台帳のテスト（1 モジュール 1 プロセス） | `test_play_policy_family_plan`・`test_stop_policy_classification`・`test_implementation_assumptions`・`test_normalization_revalidation` の 4 モジュール・65 件、すべて成功 |
| 主張の確かめに使った既存のテスト（1 モジュール 1 プロセス） | `test_setup`・`test_pokemon_check`・`test_pokemon_check_v0_3b`・`test_marker_check_field_reset_v0_91`・`test_darkness_metal_energy_v0_78`・`test_damage_reactions_poison_sleep_v0_119`・`test_deferred_shortage_user_promos_v0_127`・`test_fossil_hidden_info_v0_47`・`test_remaining_stadiums_v0_74`・`test_sudden_death_v0_134` の 10 モジュール・366 件、すべて成功 |
| データの検査（`extract_kyuura_cards.py --check`・`extract_species_heights.py --check`・`check_card_sources.py`・`check_research_links.py --kyuura ../kyuura`） | 4 件とも終了コード 0 |
| 変えていないことの確かめ | `git diff 8164194 -- kyuura_engine tests/fixtures` は空（エンジン・カードの写し・固定デッキ・参照データ）。kyuura は `b9e7cff` のまま、作業ツリーに変更なし |
| ruff 0.17.2（同じ設定・同じ対象。基点の木と今の木） | 規則ごとの数が同じ（492 件と 492 件）。新しいファイルは問題 0。新しい抑制はない |
| 道具の対戦（6 章） | 旧バッチの全 108 バッチ（4,356 局）と延長戦の道具（400 局）。終了コード 0 でないのは v0.132（予期しない拒否の 2 局。v0.136 の記録と同じ） |
| 比較プローブ（7 章） | `PSP-NJ1-NINJA-GYM-ORACLE` を検出（記録は `C:/dev/kyuura-engine-play-policy-evidence/probe_nj1.txt`） |

v0.141 の報告の訂正: v0.141 の作業の最後の報告では、停止の方針の台帳の `--check` を「問題 0」と書きました。実際は、確かめのコマンドの終了コードを、パイプの後ろの `tail` の
終了コードで読んでいて、台帳と現行コードの違い（上の行）を見落としていました。この版で作り直し、終了コードを直接読んで確かめました。

## 12. 経過（後の版）

- v0.142（[ruleset-foundation-v0.142.md](ruleset-foundation-v0.142.md)。2026-11-04）: S1 の基盤を実装した（規約集合の識別・版の管理の設計方針を利用者が承認）。実装した集合は今の挙動の集合（`CS-KYUURA-CURRENT@1`）と
  旧状態用の集合だけで、この文書の規約案 27 件は 1 つも採用していない（どれも `proposal` のまま）。止める箇所の照会はどの場面でも「続行規約なし」。S1 の完了の基準の「厳密の集合（基礎集合だけ）」は、
  DEC-BASELINE-NONUSER が未決なので、承認のない今の挙動の記録を含む今の挙動の集合で確かめた（v0.142 の文書 9 章）。この版で台帳に新しい停止コード `UNSUPPORTED_CONVENTION_SET`（E）が加わり、
  生成した集計（3 章など）はその値で作り直した。上の章の案・調査の記録は当時のまま
