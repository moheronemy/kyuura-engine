# S2a の続行規約 5 件の仕様案

<!-- この文書は scripts/build_play_policy_s2a_spec.py が docs/play-policy-s2a-spec.json と同じ元から作る。手で直さない（--check が違いを見つける） -->

**これは仕様案です。** 利用者が承認したのは進め方（2026-11-04）で、ここに書いた 5 規約の中身（補償の数・時点・範囲・除外）は承認されていません。エンジンの動作・同梱の規約集合・カードデータ・固定デッキ・参照データは変えていません。続行の処理の実装・有効化は、この仕様案の採用のあとの別の作業です。

**経過（v0.143）**: この仕様案の 5 規約は採用され、開発用の部分的な集合 CS-KYUURA-PLAY-S2A@1 として実装しました（13 章）。1〜12 章は提案の時点の記録のまま残しています。

## 1. 基点と範囲

- 基点: `fcb8bc808d65a136264e855818475e3cb2773535`（版 0.142.0。origin/claude/ruleset-s1-foundation（v0.142 の最後のコミット。2026-11-04 に fetch して確かめた））。S1（規約集合の識別・照会の入口）と共通規約の設計案の両方を含む公開済みのコミットが fcb8bc8 だけなので、main ではなくこれを基点にした。
- 含むもの: v0.141 8164194ca289c5f7f332c7f16d7f700a81a37215、共通規約の設計案 0a3ee994f3d9a89a5e3a536e7b0ab9be9900a5fa、v0.142（S1）fcb8bc808d65a136264e855818475e3cb2773535。
- `origin/main` は `816bcffb86edeb3ea713ee08818a070e036fe0a8`（v0.140 のマージ（PR #35）。v0.141・共通規約の設計案（8164194・0a3ee99）・v0.142（fe28f1d〜fcb8bc8）を含まない）。
- 作業ブランチ: `claude/play-policy-s2a-spec`。利用者の `.claude/` はコミットに入れていません。
- kyuura: kyuura は読んでいない（この仕様は、エンジンの記録・固定した研究基準の写しの参照だけ）。変更・コミット・push をしていない。
- 読んだもの: docs/ruleset-foundation-v0.142.md・docs/play-policy-family-plan.md / .json・docs/ruleset-mode-design.md・docs/ruleset-mode-decisions.md・停止の方針の台帳・研究の対応表、engine.py（準備）・procedures.py（ポケモンチェック）・interruption.py・resolution/programs.py と effects.py の DU1・TW1 の登録・conventions.py、docs/fossil-hidden-info-v0.47.md・docs/deferred-shortage-user-promos-v0.127.md・docs/rules-2000-02-14.md の p.308 の行。

## 2. 承認の記録（進め方と、具体的な続行仕様の区別）

**進め方の承認**（user_agreed・2026-11-04。進め方（エンジンの設計方針）。公式の裁定・研究上の解決ではない）:

- 基礎集合に関する全仮定の採否を先に完了させる必要はない
- 現行挙動を保持する集合へ、明示的な続行規約を追加する
- 未承認の仮定は、未承認という位置づけを維持する
- S2a の対象事例から規約参照を接続し、全 399 事例の接続を先に完成させない
- 5 規約（切り直しの補償・化石と人形の初手・ポケモンチェックの両側コイン・コインで決まる枚数の不足・ポケモンチェックでのきぜつ判定）を具体化し、一組として採用判断できる形にまとめる

含まないもの: 補償の枚数・処理の時点・適用範囲など、続行規約の具体的な中身（この仕様案の推奨・代替案はどれも未承認）。

**具体的な続行仕様の承認**: `not_approved`。この仕様案（5 規約の中身・除外・依存・実装の段階）は、利用者の採用の判断を待つ。採用まで、エンジンに登録・有効化しない。

## 3. 基本方針

- 厳密側の現行集合 CS-KYUURA-CURRENT@1 は、同じ ID・版のまま中身を変えない。未決場面では従来どおり止まる。
- 続行側は、承認された規約の対象の事例だけ続ける。対象でない事例・除外の事例は、続行側でも今の停止コードで止まる。
- 両側は同じ処理の基盤（engine.py・procedures.py・resolution/）に規約集合を渡す。モード名・カード ID の分岐を加えない。
- 既存の利用者の指定（11 件。USER-*）は両側で同じ（基礎集合）。
- 情報漏れ・内部エラー・機能不足・探索や組合せの上限を、規約で迂回しない。
- サイドを取る順番（USER-PRIZE-ORDER-ALWAYS-CHOSEN・USER-PRIZE-ORDER-PER-PLAYER）は採用済みの利用者の指定で、この仕様の対象にしない（再承認・変更しない。ポケモンチェックへ広げない）。
- 5 規約だけを加えた集合を「すべての未決場面で停止しない完成したプレイ用集合」と呼ばない（完全性は halts_at_undecided のまま）。
- 停止の例外を捕まえて無視する構造にしない。続行は、止める理由を作る分岐の手前で規約を引き、規約があれば止める理由を作らない形にする。

## 4. 一括で採用を判断するための要約

| 規約（案） | 対象 | 推奨 | 主な除外 | 観測の局 |
|---|---|---|---|---:|
| `PC-SETUP-MULLIGAN-COUNT@1` 切り直しの補償 | 両方のプレイヤーが切り直した回は補償に数えない。片方のプレイヤーだけが切り直した回を補償に数える。サドン・デスの延長戦の準備にも同じ規約を当てる | 回ごとに数える（片方だけの回 1 回につき補償 1 回） | 片方だけの回しかない切り直し<br>両方の回しかない切り直し<br>化石・人形がある手札の切り直しの前の停止 | 17 |
| `PC-SETUP-PLAY-AS-POKEMON@1` 化石・人形の初手 | 化石・人形（ポケモンとして場に出せるトレーナー）を、準備の初手のたねポケモンに数えない | 数えない（切り直す。配置でも選べない） | 準備でない場面の同じカード（にげる PF2・育て屋 PF3・ちえくらべ MG2）<br>たねポケモン・ベイビィポケモンもある手札の切り直しの判定<br>対戦が始まってからのベンチへの使用（PlayTrainer） | 28 |
| `PC-CHECK-SIDE-ORDER@1` ポケモンチェックの両側コイン | ポケモンチェックの同じ段階で両方のプレイヤーがコインを投げるときは、番を終えたプレイヤーから処理する | 番を終えたプレイヤーから | ポケモンチェックの 1 の悪エネルギーの効果・きのみの順番（BY1）<br>くろこげマーカーのコインが上限（6 枚）を超える<br>コインの前の確かめの組の上限 | 37 |
| `PC-COIN-COUNT-SHORT@1` コインで決まる枚数の不足 | 指定した対象の範囲で、存在する枚数まで処理する | あるだけ処理する | 怪電波マシーンの、はがせるエネルギーカードがない相手への使用（TW2）<br>ひかるバンギラス neo4-082 の 2 つのワザ<br>使う前・宣言の前に決まる枚数が足りない | 13 |
| `PC-CHECK-KO-POINT@1` ポケモンチェックでのきぜつ判定 | 指定したチェックの段階を終えてから、まとめてきぜつを判定する | 2 のあとに 1 回だけ判定 | 2 のあとの両方のプレイヤーのきぜつ<br>1 の中の順番（途中で HP 以上になり、きのみで HP より小さくなるポケモンを含む）<br>［ずらかる］が 1・2 の途中で残りHP「10」を通る | 0 |

- 5 規約は互いに依存せず（requires なし）、対象の場面が重なりません。一組として採用し、実装は 9 章の段階で進めます。
- 観測の局は、共通規約の設計案の計測（4,356 局・止まった 115 局）のうち、各規約の停止コードで止まった局です（計 95 局。10 章）。
- 5 規約だけを加えた集合は、すべての未決場面で止まらない完成したプレイ用の集合ではありません（ほかの未決場面では今の停止コードで止まります）。

## 5. 規約ごとの仕様

### 5.1 `PC-SETUP-MULLIGAN-COUNT@1` — 切り直しの補償

状態: `proposed`・承認: `not_approved`。共通規約の設計案の候補 `PC-SETUP-MULLIGAN-COUNT`（proposal のまま）を具体化したもの。判断事項: DEC-MULLIGAN-COMPENSATION。

| 項目 | 内容 |
|---|---|
| 原則 | 両方のプレイヤーが切り直した回は補償に数えない。片方のプレイヤーだけが切り直した回を補償に数える。サドン・デスの延長戦の準備にも同じ規約を当てる |
| 規約の文 | 準備の切り直しを回ごとに数える。片方のプレイヤーだけが切り直した回 1 回ごとに、もう一方のプレイヤーに補償 1 回（DrawMulliganCards 1 回。山札から 0〜2 枚）を与え、両方のプレイヤーが切り直した回は数えない。補償はサイドを置いたあと、ジャンケンの前（今の補償と同じ時点） |
| 適用条件 | engine._deal_opening_hands の切り直しの回の並び（mulligan_rounds）に、両方の回と片方だけの回が両方ある（今 UNRESOLVED_MULLIGAN_COMPENSATION で準備を止める条件そのもの） |
| 停止コード | `UNRESOLVED_MULLIGAN_COMPENSATION` |
| 対象の事例 | `UNRESOLVED_MULLIGAN_COMPENSATION#initial-setup`（full）: 補償の権利を与えたあとは今の準備の処理（配置・サイド・補償・ジャンケン）で、この分岐のあとにほかの停止はない（コードで確かめた）<br>`UNRESOLVED_MULLIGAN_COMPENSATION#sudden-death-segment`（full）: 延長戦の区間も同じ関数（engine._prepare_segment → _deal_opening_hands） |
| 除外 | 片方だけの回しかない切り直し: 今の補償のまま（片方だけの回の数ぶん）。この規約の数え方と結果が同じなので、規約を当てたログも書かない<br>両方の回しかない切り直し: 今のまま、どちらも引かない（p.308）<br>化石・人形がある手札の切り直しの前の停止（`UNRESOLVED_PLAY_AS_POKEMON_SETUP#initial-setup`）: PC-SETUP-PLAY-AS-POKEMON の場面（切り直しの回の前に止める別の問い） |
| 厳密側 | 両方の回と片方だけの回が両方あれば、準備で HALTED（UNRESOLVED_MULLIGAN_COMPENSATION。補償の権利を与えない）。今のまま |
| 続行側 | 止めずに、片方だけの回の数 m を、もう一方のプレイヤーの補償の回数（mulligan_draws_remaining）にする。補償の権利を与える前に、ログに規約を当てたこと（convention_applied: 規約 ID・版・場面・両方の回の数 k・片方だけの回の数 m・補償を受けるプレイヤー）を書く |
| 依存・関係・競合 | 依存: なし。関係: PC-SETUP-PLAY-AS-POKEMON。競合: なし |
| 実装箇所 | `kyuura_engine/engine.py::_deal_opening_hands`<br>`kyuura_engine/engine.py::_prepare_segment`<br>`kyuura_engine/engine.py::_after_prizes`<br>`kyuura_engine/engine.py::_draw_mulligan_cards` |
| 共通処理 / カード固有 | _deal_opening_hands の止める分岐の手前で、事例（_setup_case）を渡して続行規約を引く。規約があれば補償の数を与え、なければ今どおり止める。延長戦も同じ関数 / なし |
| 既存のテスト | `tests/test_setup.py::test_opponent_may_draw_up_to_two_per_mulligan_after_prizes`<br>`tests/test_setup.py::test_no_draw_when_both_players_had_no_basic`<br>`tests/test_setup.py::test_unequal_mulligans_after_both_mulliganed_is_halted`<br>`tests/test_sudden_death_v0_134.py::test_halted_setup_is_kept` |
| 追加する回帰テスト | 続行側: (k, m) = (1, 1)・(1, 2)・(2, 1) の盤面で、補償の回数・DrawMulliganCards の受け付け（0〜2 枚・3 枚は拒否）・ログ（convention_applied と mulligan_draw）・観測<br>両側: (0, m)・(k, 0) の盤面が今と同じ（状態・乱数・ログ・観測。convention_applied を書かない）<br>延長戦の区間（#sudden-death-segment）でも同じ<br>厳密側（CS-KYUURA-CURRENT@1）では (1, 1) が今と同じ HALTED（停止コード・理由の文・ログ）<br>補償で引いたたねポケモンを準備で出せない（配置は終わっている）こと、番の中では出せること |
| 現行挙動からの差 | 今止まる k ≥ 1・m ≥ 1 の場合だけ、止めずに補償 m 回を与える。k = 0 または m = 0 は状態・乱数・ログとも今と同じ |
| 設計案からの差 | 設計案の候補と同じ推奨。この仕様で「回」の定義・回の並び（コードで確かめた）・上限・選ぶ人と時点・補償で引いたたねの扱いを書き足した |
| 推奨 | 回ごとに数える（片方だけの回 1 回につき補償 1 回）（p.308 の 2 つの文（切り直し 1 回ごとの補償・両方のときはどちらも引かない）を回ごとにそのまま当てはめる読み方で、k = 0・m = 0 の今の結果と同じ式（片方だけの回の数）になる。席・先攻後攻によらず、新しい決定・乱数の消費がない） |
| 代替案 | 両方の回が一度でもあれば、どちらも引かない（「両方とも」の文を準備全体に当てはめる読み方。片方だけの追加の切り直しで、相手が補償を受けられない）<br>相手の切り直しの総数ぶん引ける（両方の回も数える）（「両方とも…引かない」の文と合わない（採らない案として記録）） |
| 未確認 | 公式資料に回数が違う場合の記述がないことの再確認（研究上は未解決のまま。この規約は研究上の解決ではない） |

具体化した点:

- **「回」の定義**: _deal_opening_hands の 1 回の判定。手札にたねポケモンカード・ベイビィポケモンカードのないプレイヤーの組（lacking）を求め、その全員が手札を見せて山札にもどし、切って 7 枚引き直す。mulligan_rounds の 1 要素で、組が 2 人なら両方の回、1 人なら片方だけの回。
- **回の並び（コードで確かめた）**: 片方だけの回のあと、もう一方のプレイヤーは引き直さない（dealing が lacking に絞られる）。並びはいつも「両方の回 k 回 → 同じ 1 人の片方だけの回 m 回」（k・m ≥ 0）で、片方だけの回のあとに両方の回は来ない。両方のプレイヤーが片方だけの回を持つことはない。
- **1 回の補償と上限**: 片方だけの回 1 回につき補償 1 回。1 回の補償は DrawMulliganCards 1 回で、山札から 0〜rules.mulligan_draw_max_per_mulligan（2）枚（今のまま）。補償の回数は m 回で、回数の上限は設けない（今の片方だけの補償も上限なし）。1 回に引けるのは山札の枚数まで（既存の INVALID_DRAW_COUNT）。
- **引くかを誰がいつ選ぶか**: 補償を受けるプレイヤー（片方だけの回をしなかったプレイヤー）が、両方が最初のポケモンを出してサイドを置いたあと（段階 SETUP_MULLIGAN_DRAW）、ジャンケン（ReportJankenResult）の前に、1 回ずつ枚数（0〜2）を選ぶ。今と同じコマンド・同じ時点。
- **サイドとの前後**: サイドを置いたあと（p.308「サイドをセットした後で」。engine._after_prizes。今と同じ）。
- **片方だけが最初から切り直す（k = 0）**: 今の補償 m 回と同じ（この規約は結果を変えない）。
- **両方の回のあと、片方だけが追加で切り直す（k ≥ 1・m ≥ 1）**: この規約の対象。補償は m 回（k 回の両方の回は数えない）。
- **補償でたね・ベイビィを引いた場合**: 手札に加わるだけ。最初のポケモンの配置は終わっているので出し直さず、切り直しの回にも数えない。先攻・後攻の番が始まってから通常どおり出せる（今と同じ）。
- **ほかの準備の未決場面との依存**: 各回の判定の前に、化石・人形の場面（UNRESOLVED_PLAY_AS_POKEMON_SETUP）がある。PC-SETUP-PLAY-AS-POKEMON のない集合では、化石・人形がある手札は回の前に今どおり止まる。この規約は PC-SETUP-PLAY-AS-POKEMON を必要としない。PC-SETUP-PLAY-AS-POKEMON を加えると、化石・人形だけの手札が切り直しの回になり、この規約の場面（両方 → 片方）に当たる対戦が増える。

### 5.2 `PC-SETUP-PLAY-AS-POKEMON@1` — 化石・人形の初手

状態: `proposed`・承認: `not_approved`。共通規約の設計案の候補 `PC-SETUP-PLAY-AS-POKEMON`（proposal のまま）を具体化したもの。判断事項: DEC-PLAY-AS-POKEMON。 研究の記録: PF1。

| 項目 | 内容 |
|---|---|
| 原則 | 化石・人形（ポケモンとして場に出せるトレーナー）を、準備の初手のたねポケモンに数えない |
| 規約の文 | 準備の切り直しの判定と最初のポケモンの配置では、ポケモンとして場に出せるトレーナー（なにかの化石・ピッピ人形）を、たねポケモンカードとして数えない。たねポケモンカード・ベイビィポケモンカードがない手札は、今の切り直しと同じく切り直す。対戦が始まってからベンチに出す処理（v0.47）は変えない |
| 適用条件 | 準備（最初の対戦・延長戦の区間）で、(1) たねポケモンカード・ベイビィポケモンカードのない手札に、登録の型が PlayAsPokemon のカードがある（今 UNRESOLVED_PLAY_AS_POKEMON_SETUP で準備を止める条件）、(2) PlaceStartingPokemon で、そのカードを最初のポケモンに選んだ（今 UnsupportedError UNRESOLVED_PLAY_AS_POKEMON_SETUP で拒否する条件） |
| 停止コード | `UNRESOLVED_PLAY_AS_POKEMON_SETUP` |
| 対象の事例 | `UNRESOLVED_PLAY_AS_POKEMON_SETUP#initial-setup`（question_resolved_other_stops_possible）: 切り直したあとの回で、PC-SETUP-MULLIGAN-COUNT の場面（両方 → 片方）に当たりうる。その規約のない集合ではそこで止まる<br>`UNRESOLVED_PLAY_AS_POKEMON_SETUP#sudden-death-segment`（question_resolved_other_stops_possible）: 同じ<br>`UNRESOLVED_PLAY_AS_POKEMON_SETUP#setup-placement`（full）: 台帳にまだない事例（proposed_cases）。今は拒否の箇所で、S1 の照会は未接続（docs/ruleset-foundation-v0.142.md 8 章） |
| 台帳に加える事例（案） | `UNRESOLVED_PLAY_AS_POKEMON_SETUP#setup-placement`: 準備（最初の対戦・延長戦の区間）の PlaceStartingPokemon で、ポケモンとして場に出せるトレーナーを最初のポケモンに選んだ（engine._place_starting_pokemon の拒否） |
| 除外 | 準備でない場面の同じカード（にげる PF2・育て屋 PF3・ちえくらべ MG2）（`UNRESOLVED_PLAY_AS_POKEMON_RETREAT`）: 同じカードでも別の問い。UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON・UNRESOLVED_MIND_GAMES_PLAY_AS_POKEMON も同じく対象外<br>たねポケモン・ベイビィポケモンもある手札の切り直しの判定: 今のまま切り直さない（今も止めない）<br>対戦が始まってからのベンチへの使用（PlayTrainer）: v0.47 の処理のまま。「初手のたねに数えない」を、対戦中に使えない意味へ広げない |
| 厳密側 | 化石・人形があって、たね・ベイビィのない手札で準備を HALTED（切り直す前）。配置で選ぶと UnsupportedError。どちらも今のまま |
| 続行側 | 切り直す（ログに convention_applied を書いてから mulligan）。配置で選ぶと規約による拒否（入力の状態・乱数・ログは変えない。別のカードを選び直せる） |
| 依存・関係・競合 | 依存: なし。関係: PC-SETUP-MULLIGAN-COUNT。競合: なし |
| 実装箇所 | `kyuura_engine/engine.py::_deal_opening_hands`<br>`kyuura_engine/engine.py::_place_starting_pokemon`<br>`kyuura_engine/engine.py::_hand_has_basic`<br>`kyuura_engine/effects.py::play_as_pokemon_in_hand` |
| 共通処理 / カード固有 | _deal_opening_hands の止める分岐と _place_starting_pokemon の拒否の手前で、事例を渡して続行規約を引く。_hand_has_basic（たね・ベイビィの判定）は変えない / 対象カードの一覧は登録の型（PlayAsPokemon）から求める。規約の中身は識別の条件で、今の 2 枚は参照の記録（--check がカードの一覧の変化を見つける） |
| 既存のテスト | `tests/test_fossil_hidden_info_v0_47.py::test_setup_with_a_fossil_and_no_basic_pokemon_halts`<br>`tests/test_fossil_hidden_info_v0_47.py::test_fossil_cannot_be_placed_as_a_starting_pokemon` |
| 追加する回帰テスト | 続行側: 化石だけ・人形だけ・化石と人形の手札で切り直すこと（回数・mulligan の公開・convention_applied・乱数の位置）<br>続行側: たね・化石の手札で切り直さず、化石を配置に選ぶと NOT_BASIC_POKEMON（状態・乱数・ログが変わらない）、たねだけを出せる<br>化石・人形だけの手札が両方の回 → 片方だけの回になる盤面: PC-SETUP-MULLIGAN-COUNT がある集合では補償、ない（開発用の）集合では UNRESOLVED_MULLIGAN_COMPENSATION で止まる<br>延長戦の区間でも同じ<br>対戦中の PlayTrainer でベンチに出す処理・にげる（PF2）・育て屋（PF3）が両側で今と同じ<br>厳密側では、準備の停止・配置の拒否が今と同じ |
| 現行挙動からの差 | 続行側だけ: 今止まる手札で切り直す（切り直しの回・公開・乱数の消費が増える）。配置の拒否のコードが UnsupportedError から規約による IllegalActionError になる |
| 設計案からの差 | 設計案の候補は切り直しの判定だけを書いていた。この仕様は、同じ問い（PF1: 準備で、たねポケモンとして扱えるか）の配置の拒否を、新しい事例 #setup-placement として加えた |
| 推奨 | 数えない（切り直す。配置でも選べない）（準備の規定の「たねポケモンカード」の語のまま当てはめ、最初のポケモンとしてトレーナーを置く新しい処理（裏向きで置く・表にする）を作らない。切り直しと配置で同じ答えにする） |
| 代替案 | 最初のポケモン（バトル場・ベンチ）として出せる（カードの「たねポケモンとして場に出せる」を準備にも当てはめる読み方。準備で置く処理と、裏向きで置くときの扱いの確かめが要る（実装が要る））<br>切り直しの判定だけ決め、配置は今の UnsupportedError のまま（全体を止める場面だけを続ける最小の案。切り直しの判定と配置で答えが分かれる） |
| 未確認 | kyuura の UQ-PLAY-AS-POKEMON の記録の再照合（固定コミットの写しの参照だけ）<br>公式資料に準備での扱いの記述がないことの再確認 |

具体化した点:

- **対象カードと共通の識別条件**: 登録した実装の型が PlayAsPokemon（effects.play_as_pokemon_in_hand が見る、ポケモンとして場に出せるトレーナー）のカード。今の登録はなにかの化石（PMCG3-046）・ピッピ人形（PMCG1-091）の 2 枚。カード ID で分けず、登録の型で識別する（engine.py にカード ID の分岐を加えない）。
- **化石・人形だけで、たね・ベイビィがない手札**: たねポケモンのない手札として、今の切り直しと同じく切り直す（手札を見せる・山札にもどす・切る・7 枚引く。ログ mulligan の revealed_hand に化石・人形も入る）。
- **通常のたね・ベイビィもある手札**: 切り直さない（今と同じ）。最初のポケモンには、たね・ベイビィだけを出せる。
- **初期配置と、対戦開始後に出す処理の区別**: 準備の PlaceStartingPokemon で化石・人形を選ぶと、続行側は規約による拒否（IllegalActionError。コードは、たねポケモンでないカードの既存の拒否と同じ NOT_BASIC_POKEMON を推奨。理由の文に規約 ID を書く）。厳密側は今の UnsupportedError（UNRESOLVED_PLAY_AS_POKEMON_SETUP）のまま。対戦が始まってからの PlayTrainer でベンチに出す処理は変えない。
- **切り直しの回数・補償との関係**: 化石・人形だけの手札による切り直しも 1 回の回に数える（両方・片方だけの判定は PC-SETUP-MULLIGAN-COUNT と同じ）。補償は、片方だけの回だけなら今の補償、両方 → 片方の並びなら PC-SETUP-MULLIGAN-COUNT（その規約のない集合ではそこで止まる）。
- **サドン・デスへの適用**: 延長戦の区間の準備も同じ処理（engine._prepare_segment）なので同じ規約を当てる（#sudden-death-segment）。
- **ベイビィの初手の規則**: GR-2000-P308-BABY-SETUP（ベイビィだけの手札は切り直さない・最初のポケモンに出せる）は変えない。

### 5.3 `PC-CHECK-SIDE-ORDER@1` — ポケモンチェックの両側コイン

状態: `proposed`・承認: `not_approved`。共通規約の設計案の候補 `PC-CHECK-SIDE-ORDER`（proposal のまま）を具体化したもの。判断事項: DEC-SLEEP-COIN-ORDER, DEC-ORDER-RULE。 研究の記録: KK1, Z29。

| 項目 | 内容 |
|---|---|
| 原則 | ポケモンチェックの同じ段階で両方のプレイヤーがコインを投げるときは、番を終えたプレイヤーから処理する |
| 規約の文 | ポケモンチェックの同じ段階で、両方のプレイヤーが同じ種類のコイン（3 のねむりのコイン、1 のくろこげマーカーのコイン）を投げるときは、その番を終えたプレイヤー（ポケモンチェックの直前の番のプレイヤー）の場から先に、次に相手の場の順に投げて処理する。それぞれの場はバトル場 → ベンチの並び。決定は出さない |
| 適用条件 | procedures.pokemon_check_sleep_and_paralysis で両方の対戦ポケモンがねむり（今 UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER で止める条件）、procedures._char_coin_stop で両方のプレイヤーの場にくろこげマーカーののったポケモンがある（今 UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER で止める条件。KK1） |
| 停止コード | `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`<br>`UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER` |
| 対象の事例 | `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（question_resolved_other_stops_possible）: 順番を決めたあと、回復したときの止め方（MH1・TF1・TF2・DG1）が残る。続行側では、回復の結果のすべての組で確かめる（下の details）<br>`UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER`（question_resolved_other_stops_possible）: 順番を決めても、コインの前の確かめ（どの結果でも 1・2 の確かめで止めないか）と上限 MAX_CHAR_COINS が残る |
| 除外 | ポケモンチェックの 1 の悪エネルギーの効果・きのみの順番（BY1）（`UNRESOLVED_POKEMON_CHECK_BERRY_ORDER`）: 両方の側の順番だけでなく、効果の種類（悪エネルギー・くろこげマーカー・きのみ）の順番を含む別の問い。この規約で解かない（設計案では unverified の対象だった）<br>くろこげマーカーのコインが上限（6 枚）を超える（`UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`）: 技術的な上限（MAX_CHAR_COINS）。規約で上限を外さない<br>コインの前の確かめの組の上限（`LIMIT:MAX_CHAR_COINS`）: 同じ上限の台帳の項目<br>ポケモンチェックの 2 のあとの両方のきぜつ（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）: PC-CHECK-DOUBLE-KNOCKOUT（S2b）。この規約は扱わない<br>ポケモンチェックの外の同時の処理: PC-ORDER-ATTACK-PRECHECK・PC-ORDER-OVERLAP（一般の同時効果）へ広げない<br>サイドを取る順番: 採用済みの利用者の指定（USER-PRIZE-ORDER-ALWAYS-CHOSEN・USER-PRIZE-ORDER-PER-PLAYER）。この規約と別のもので、変えない・ポケモンチェックへ広げない |
| 厳密側 | 両方がねむり・両方の場にくろこげマーカーなら、コインを投げる前に HALTED（今のまま） |
| 続行側 | 最初のコインの前にログに convention_applied（規約 ID・版・場面・順番）を書き、規約の順に投げて処理を続ける |
| 依存・関係・競合 | 依存: なし。関係: PC-CHECK-KO-POINT, PC-CHECK-DOUBLE-KNOCKOUT。競合: なし |
| 実装箇所 | `kyuura_engine/procedures.py::pokemon_check_sleep_and_paralysis`<br>`kyuura_engine/procedures.py::_recovery_stop`<br>`kyuura_engine/procedures.py::_char_coin_stop`<br>`kyuura_engine/procedures.py::_flip_char_coins`<br>`kyuura_engine/procedures.py::pokemon_check_poison`<br>`kyuura_engine/effects.py::char_check_targets`<br>`kyuura_engine/effects.py::sleep_check_coins` |
| 共通処理 / カード固有 | 2 か所の止める分岐の手前で続行規約を引く。順番は今の order（番を終えたプレイヤー → 相手）のまま。ねむりは回復の組の確かめを加える / なし（くろこげマーカー・［ふかいねむり］の登録は今のまま） |
| 既存のテスト | `tests/test_rocket_snorlax_v0_17b.py::test_both_actives_asleep_halts_the_pokemon_check`<br>`tests/test_confusion.py::test_sleep_coin_order_stop_is_unchanged`<br>`tests/test_marker_check_field_reset_v0_91.py::test_both_players_flip_stops_before_coins`<br>`tests/test_marker_check_field_reset_v0_91.py::test_double_knock_out_possible_stops_before_coins`<br>`tests/test_pokemon_check_v0_3b.py::test_order_poison_then_sleep_then_paralysis` |
| 追加する回帰テスト | 続行側: 両方ねむりで、番を終えたプレイヤーが先に投げること（両方の番の終わりで）、コインの割り当て・回復・ログ（convention_applied → sleep_check の順）<br>続行側: 先の回復で後のコインの枚数（［ふかいねむり］）が変わる・変わらない盤面で、投げる直前の場で枚数を決めること<br>続行側: 両方の回復の組で MH1 などが起こる盤面で、コインの前にその停止コードで止まること（組を確かめない誤りを見つける）<br>続行側: 両方の場のくろこげマーカーで、コインの前の確かめが今どおりはたらき（BY1・PK1・SC1・両方のきぜつで止める組）、上限を超えると UNSUPPORTED のまま<br>両側: 片方だけのねむり・片方だけのくろこげマーカー・ねむりとマヒが今と同じ<br>厳密側では今と同じ HALTED |
| 現行挙動からの差 | 続行側だけ: 今止まる 2 つの場面でコインを投げて続ける。回復の組の確かめは続行側の新しい確かめ（厳密側では起こらない場面） |
| 設計案からの差 | 設計案の候補は UNRESOLVED_POKEMON_CHECK_BERRY_ORDER を unverified の対象にしていた。この仕様では対象から除いた（BY1 は効果の種類の順番を含む別の問い）。ねむりの回復の組の確かめ・反映の時点を書き足した |
| 推奨 | 番を終えたプレイヤーから（席（プレイヤー 0・1）によらず、今のログの順・p.325 の「番のプレイヤー」に近い。決定を増やさない。番を終えたプレイヤーは番ごとに入れかわる） |
| 代替案 | 番を終えたプレイヤーが順番を選ぶ（決定を出す）（p.325 の決める人を当てはめる読み方。決定が増え、方策・ログが変わる）<br>次の番のプレイヤーから（席によらないが、根拠が弱い）<br>ねむりは両方が投げてから、まとめて反映する（反映の時点の別の読み方。先の回復で後のコインの枚数が変わる盤面だけ結果が違う（今の写しで起こるかは未確認）） |
| 未確認 | 先の回復が後のコインの枚数・回復の止め方を変える盤面が、今の写しで作れるか（到達可能性）<br>BY1 の問いの中身（効果の種類の順番）。この規約では扱わない<br>先攻・後攻の偏り（勝率の差）の計測はまだしていない |

具体化した点:

- **対象の事例**: (1) ポケモンチェックの 3 で、両方の対戦ポケモンがねむり（特殊状態はバトル場のポケモンだけなので、それぞれの側に 1 匹）。(2) ポケモンチェックの 1 で、両方のプレイヤーの場にくろこげマーカーののったポケモンがある（依頼の「やけどマーカー」は、この版のデータのくろこげマーカー（マグマラシの［やきこがす］））。
- **コインの順番と、チェックの段階の順番の区別**: この規約が決めるのは、同じ段階の中で両方のプレイヤーが投げるコインの順番だけ。段階の順番（1 の悪エネルギー → くろこげマーカー → きのみ、2 のどく、きぜつの判定、3 のねむり、4 のマヒ）は変えない。
- **順番**: 番を終えたプレイヤー（ポケモンチェックの時点の state.current_player）の場、次に相手の場。それぞれの場はバトル場 → ベンチ（in_play() の並び）。今のログの順と同じ。
- **両方が同じ状態・違う状態**: 両方がねむり、両方の場にくろこげマーカー: この規約の順。片方がねむりで片方がマヒ、片方の場だけにくろこげマーカー: コインを投げるのは片方だけなので今のまま（規約は当たらない）。
- **片方だけが判定を要する**: 今のまま（そのプレイヤーだけが投げる）。
- **コインの結果を反映する時点**: くろこげマーカー: すべてのコインを先に投げ（今の _flip_char_coins）、「うら」の 20 ダメージは 1 の処理の中（悪エネルギーのあと、きのみの前）で与える（今と同じ）。ねむり: 番を終えたプレイヤーがコインを投げて結果をすぐ反映し（「おもて」なら回復）、そのあと相手が投げて反映する（今の処理の並び）。相手のコインの枚数（［ふかいねむり］）は、投げる直前の場で決める（v0.119 の共通の問い合わせ sleep_check_coins）。
- **複数の判定の安定した処理順**: 上の順。席（プレイヤー 0・1）・先攻後攻・場の番号の大小で決めない。どちらから投げるかを選ぶ決定は出さない。
- **コインの前の確かめ（続行側）**: くろこげマーカー: 今どおり、結果のすべての組で 1・2 の確かめ（_pokemon_check_plan）で止めないことを、コインの前に確かめる。ねむり: 両方の回復の結果のすべての組（4 通り。この番に回復するマヒを含む）を規約の順に複製の上で処理し、回復の止め方（_recovery_stop を組の回復に広げる。MH1・TF1・TF2・DG1）で止めないことを、コインの前に確かめる。止める組があれば、コインを投げる前に、その止め方の停止コードで止める（今の 1 匹のときと同じ形）。
- **乱数・公開の情報・きぜつの判定への影響**: コインごとの乱数の割り当てが規約の順で決まる（番を終えたプレイヤーは毎回入れかわるので、席・先攻後攻で固定しない）。コインは公開（変えない）。3・4 はダメージがなく、そのあとにきぜつの判定はない（p.323）。くろこげマーカーのダメージは 2 のあとのきぜつの判定（PC-CHECK-KO-POINT と同じ時点）。

### 5.4 `PC-COIN-COUNT-SHORT@1` — コインで決まる枚数の不足

状態: `proposed`・承認: `not_approved`。共通規約の設計案の候補 `PC-COIN-COUNT-SHORT`（proposal のまま）を具体化したもの。判断事項: DEC-STATED-COUNT-SHORT, DEC-DEFERRED-RESUME。 研究の記録: DU1, TW1。

| 項目 | 内容 |
|---|---|
| 原則 | 指定した対象の範囲で、存在する枚数まで処理する |
| 規約の文 | 共通の数量処理のチェック地点（interruption.check_quantity）で、コインの「おもて」の数で決まった枚数 H が、その時点の対象の枚数 N より多いときは、対象 N 枚をすべて処理し、足りない H − N 枚ぶんは何もしない。コインの結果（H）・ほかの処理は変えない。対象はチェック地点の要素ごとに場面で指定する（最初は DU1・TW1） |
| 適用条件 | チェック地点で H > N（N = 0 をふくむ）になる、ファイヤーのドライアップ（DU1）と怪電波マシーン（TW1）。今は途中停止（Phase.HALTED と Halt.interruption）にする条件 |
| 停止コード | `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`<br>`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT` |
| 対象の事例 | `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`（full）: N 枚の処理は今の H = N の経路（決定なし・効果の到達・［KEEP］・もどる処理）。そのあとはワザの終わり・きぜつの判定（コードを読んで確かめた。実行の確かめは実装の段階）<br>`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT`（full）: N 枚の処理は今の H = N の経路（もどす → END_TURN）（コードを読んで確かめた） |
| 除外 | 怪電波マシーンの、はがせるエネルギーカードがない相手への使用（TW2）（`UNRESOLVED_THOUGHT_WAVE_MACHINE_WITHOUT_TARGET`）: 使う前に決まる使用の条件の問い（UQ-CARD-USE-WITHOUT-TARGET）。この規約で自動的に解かない<br>ひかるバンギラス neo4-082 の 2 つのワザ: 利用者の指定（USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK・USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO）のまま。この規約の根拠にしない・指定を広げない<br>使う前・宣言の前に決まる枚数が足りない: PC-STATED-COUNT-SHORT・PC-USE-WITHOUT-TARGET（S3）。コストの不足は既存の拒否のまま<br>すでに途中停止した状態の再開: DEC-DEFERRED-RESUME（未決）。規約集合は対戦中に変えないので、厳密側で途中停止した状態は続行側で再開しない<br>ほかのカード・ほかの要素の不足: チェック地点の要素ごとに場面で指定する。新しいカード・要素は規約の場面に加える判断（規約の版を上げる）が要る<br>選ぶと止めるポケモン（色の読み方・タケシの保護・「ワザをうけない」・［KEEP］・「とうめい」・TE2 など）: 既存の問い・止め方のまま。不足と別の問いで、この規約で解かない |
| 厳密側 | H > N なら、処理する前に途中停止（Phase.HALTED・Halt.interruption。コインとそこまでの処理を残す）。今のまま |
| 続行側 | チェック地点でログに convention_applied（規約 ID・版・場面・要素・H・N・処理する数）を書き、N 枚を処理して通常どおり続ける |
| 依存・関係・競合 | 依存: なし。関係: PC-STATED-COUNT-SHORT。競合: なし |
| 実装箇所 | `kyuura_engine/interruption.py::check_quantity`<br>`kyuura_engine/interruption.py::interrupt`<br>`kyuura_engine/resolution/programs.py::shortage_classes`<br>`kyuura_engine/resolution/programs.py::DiscardChosenTypedEnergyUntilTails`<br>`kyuura_engine/effects.py::CoinsUntilTailsReturnOpponentActiveEnergyThenEndTurn` |
| 共通処理 / カード固有 | チェック地点（check_quantity）を、状態の規約集合を引いて処理する数を返す形にする。カードの登録は今の H = N の経路をそのまま使う / チェック地点の要素・対象の数え方・処理（トラッシュ・手札にもどす）はカードの登録のまま |
| 既存のテスト | `tests/test_deferred_shortage_user_promos_v0_127.py::test_boundaries`<br>`tests/test_deferred_shortage_user_promos_v0_127.py::test_esp_redo_is_asked_before_the_shortage`<br>`tests/test_deferred_shortage_user_promos_v0_127.py::test_shortage_keeps_the_trainer_in_transit`<br>`tests/test_deferred_shortage_user_promos_v0_127.py::test_checkpoint_only_raises_on_shortage`<br>`tests/test_deferred_shortage_user_promos_v0_127.py::test_shortage_classes`<br>`tests/test_deferred_shortage_user_promos_v0_127.py::test_tampered_logs_are_found` |
| 追加する回帰テスト | 続行側: DU1 で N = 0・1・2・5 に対する H = N + 1・N + 9 の処理（N 枚のトラッシュ・決定なし・ログの H・convention_applied）<br>続行側: TW1 で H > N のとき N 枚を手札にもどし、使用中のカードをトラッシュして番を終える<br>続行側: ESP で最初 H > N・やり直して H ≤ N / H > N の両方<br>続行側: 効果の到達がない・［KEEP］で無効な対象（チェック地点のあとの処理が今どおり）<br>続行側: 先読みが N + 1 の組を通常の完了として数えること・上限を緩めないこと<br>ログの監査が、続行側のログ（min(H, N) と convention_applied）を受け付け、数を変えたログ・convention_applied のないログを見つけること<br>厳密側では今と同じ途中停止（記録・在途のカード・観測）。TW2 は両側で同じ拒否 |
| 現行挙動からの差 | 続行側だけ: 途中停止の代わりに N 枚を処理して続ける（ログに convention_applied が増える。H は同じ） |
| 設計案からの差 | 設計案の候補と同じ推奨。この仕様で、0 枚・宣言の条件との区別・防護・ESP・番の終わり・途中停止から通常の完了へ進むための処理（先読み・監査・不変条件）を書き足した |
| 推奨 | あるだけ処理する（コインのあとなので「使えない」にできず、途中停止のまま再開の操作もない（GAP-DEFERRED-HALT-NO-RESUME）。コインと H を変えずに、説明の範囲の対象をすべて処理する） |
| 代替案 | 効果全体を何もしない（足りなければトラッシュ・もどすをしない）（結果が大きく変わる。根拠が弱い） |
| 未確認 | チェック地点のあとの処理（あるだけにしたあとの続き）を実行して確かめていない（コードを読んだだけ）<br>公式資料に足りないときの記述がないことの再確認（UQ-STATED-COUNT-SHORT は未解決のまま） |

具体化した点:

- **対象カード・事例 ID・停止コード**: ファイヤー（ES2-005・QSG-055）の［ドライアップ］: 事例・停止コード UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT（DU1。要素 discard_water_energy_cards）。怪電波マシーン（neo4-108）: UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT（TW1。要素 return_energy_cards_to_hand）。
- **コインで決まった数と、実際の対象の数**: H ≤ N は今のまま（H = 0 は何もしない、H = N はすべて、0 < H < N は使ったプレイヤーがちょうど H 枚を選ぶ）。H > N は N 枚すべて（選び方は 1 つなので決定を出さない）。処理する数は min(H, N) だが、コインの H は丸めずにログに残す。
- **対象が 0 枚**: DU1: 選んだポケモンの「水」エネルギーカードが 0 枚（N = 0）で H ≥ 1 なら、何もトラッシュしない（今の H = 0 と同じ結果）。TW1: 使う前の確かめ（TW2）で N ≥ 1 なので、N = 0 は起こらない。
- **宣言の条件・コストと、効果による不足の区別**: この規約はコインのあとに効果の要素で分かる不足だけ。使う前・宣言の前に決まる不足・対象なし（TW2 など）・コストの不足は対象外。
- **選ぶ人と選択肢**: 今と同じ（ワザ・トレーナーを使ったプレイヤー）。H > N では選び方が 1 つなので決定を出さない。H < N の決定（DISCARD_OPPONENT_ENERGY・RETURN_ENERGY）は今のまま。
- **防護・無効化**: DU1: チェック地点のあとの効果の到達（reaches）・［KEEP］の無効（_voided）を今どおり評価し、届かない・無効なら何もしない。選ぶと止めるポケモンは、選んだ時点で今どおり止める。TW1: タケシの保護は使う前の TW2、［でんせつのからだ］はコインの前の LB1 のまま。
- **コインの再投げ**: ナツメのESP（ワザのコインだけ。DU1）は、今どおり最初のまとまりのあとに聞き、最後の並びの H で判断する。不足でコインを途中で打ち切らない（CR-UNTIL-TAILS-NOT-CAPPED）。TW1 はトレーナーのコインで、ESP は当たらない。
- **「使ったら番が終わる」**: TW1: N 枚をもどしてから、今の H = N の経路と同じく使用中のカードをトラッシュして END_TURN。DU1: ワザの終わり・きぜつの判定へ（今の H = N と同じ）。
- **途中停止から通常の完了へ進むために要る処理**: 続行側では、チェック地点を「必要な数と処理できる数を比べ、処理する数を返す」問い合わせにし（DeferredShortage を投げない）、途中停止の記録・在途のカードを作らない。先読み（programs.shortage_classes）の N + 1 の組は、続行側では通常の完了の枝として数える（処理は H = N と同じで、ログの H だけが違う）。答えの続きを試す確かめ（_decision_has_unstopped_answer・_trainer_dead_end）・ログの監査（tests/log_audit.py の v127_problems）・不変条件は、続行側で「トラッシュ・もどした数 = min(H, N)」と convention_applied の記録を確かめるように広げる（厳密側の確かめは緩めない）。
- **カード固有の手順**: 残す: DU1 の対象の選択（コインの前）・「水」エネルギーカードの数え方・トラッシュ（もどる処理）、TW1 の対戦ポケモンからはがして手札にもどす・番の終わり。共通の部分はチェック地点だけ。

### 5.5 `PC-CHECK-KO-POINT@1` — ポケモンチェックでのきぜつ判定

状態: `proposed`・承認: `not_approved`。共通規約の設計案の候補 `PC-CHECK-KO-POINT`（proposal のまま）を具体化したもの。判断事項: DEC-KNOCKOUT-READINGS。 研究の記録: PK1。

| 項目 | 内容 |
|---|---|
| 原則 | 指定したチェックの段階を終えてから、まとめてきぜつを判定する |
| 規約の文 | ポケモンチェックでは、1 の「指示されたこと」（くろこげマーカーのコイン・悪エネルギーの効果・くろこげマーカーのダメージ・きのみ）と 2 の「どく」のダメージを終えてから、1 回だけきぜつを判定する。1 のあとに HP 以上のダメージになったポケモンも、その判定まで場に残り、2 のどくのダメージを受ける |
| 適用条件 | procedures._pokemon_check_plan で、1 のあとに HP 以上のポケモンがいて、procedures.mid_check_knockout_divergence が違いを返す（今 UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT で止める条件。PK1） |
| 停止コード | `UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT` |
| 対象の事例 | `UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`（question_resolved_other_stops_possible）: 違いを返す 2 つの条件（2 の問い合わせが変わる・2 の前に対戦が終わりうる）はどちらも、場に残る読み方を選べば決まる（コードで確かめた）。そのあとの両方のきぜつ・SC1・AL1 などは残る |
| 除外 | 2 のあとの両方のプレイヤーのきぜつ（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）: PC-CHECK-DOUBLE-KNOCKOUT（S2b）。今のまま止める<br>1 の中の順番（途中で HP 以上になり、きのみで HP より小さくなるポケモンを含む）（`UNRESOLVED_POKEMON_CHECK_BERRY_ORDER`）: BY1（1 の中の効果の種類の順番）。この規約は 1 の中のきぜつの判定の時点を決めない<br>［ずらかる］が 1・2 の途中で残りHP「10」を通る（`UNRESOLVED_SCRAM_TIMING`）: SC1。別の問い（今のまま止める）<br>バトル場をはなれられない効果のきぜつ・［ずらかる］（`UNRESOLVED_LEAVE_LOCK_KNOCKOUT`）: AL1（UNRESOLVED_LEAVE_LOCK_SCRAM の AL3 も同じ）<br>［ポイズンミスト］の当てはまり方・どくの量の合わせ方（`UNRESOLVED_POISON_MIST_SOURCE`）: PO1〜PO3（UNRESOLVED_POISON_CHANGE_ORDER・UNRESOLVED_POISON_MIST_EARLIER_POISON を含む）。この規約で暗黙に解かない<br>どくのダメージに当てはめる受けるダメージを変える特殊能力・色の読み方・悪エネルギーの特殊能力（`UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`）: KA1・VS1（UNRESOLVED_SHIFT_COLOR_DURATION）・DE1（UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER）。今のまま止める<br>ワザの処理の中のきぜつ: ポケモンチェックの外。今の処理のまま |
| 厳密側 | 1 と 2 のあいだの判定の時点で結果が変わるなら、ダメージを与える前に HALTED（今のまま） |
| 続行側 | ダメージを与える前にログに convention_applied（規約 ID・版・場面・HP 以上のポケモン）を書き、2 のあとに 1 回だけ判定して続ける |
| 依存・関係・競合 | 依存: なし。関係: PC-CHECK-SIDE-ORDER, PC-CHECK-DOUBLE-KNOCKOUT。競合: なし |
| 実装箇所 | `kyuura_engine/procedures.py::_pokemon_check_plan`<br>`kyuura_engine/procedures.py::mid_check_knockout_divergence`<br>`kyuura_engine/procedures.py::pokemon_check_poison`<br>`kyuura_engine/resolution/flow.py::_pokemon_check` |
| 共通処理 / カード固有 | _pokemon_check_plan の PK1 の分岐の手前で続行規約を引く / なし |
| 既存のテスト | `tests/test_marker_check_field_reset_v0_91.py::test_mid_check_knock_out_changes_the_poison_step_pk1`<br>`tests/test_shared_checks_pokemon_reuse_v0_79.py::test_gas_source_knocked_out_by_darkness_changes_kabuto_poison`<br>`tests/test_shared_checks_pokemon_reuse_v0_79.py::test_transform_changes_knock_out`<br>`tests/test_neo_trainer_components_v0_80.py::test_game_ending_reading_with_a_later_knockout_stops`<br>`tests/test_pokemon_check_v0_3b.py::test_double_poison_knock_out_still_halts_before_the_damage_and_coins` |
| 追加する回帰テスト | 続行側: 1 で HP 以上になったポケモンがどく状態のとき、どくのダメージ・2 のあとのきぜつ・ログ（convention_applied → poison_damage → knock_out）<br>続行側: かがくへんかガスの発生源が 1 で HP 以上になる盤面で、2 のどくの量が場に残る読み方のもの（KA1 の比べ）<br>続行側: 2 の前に対戦が終わりうる盤面（v0.80 の盤面）で、2 のあとに判定し、両方のきぜつなら今の DOUBLE_KNOCKOUT で止まること<br>続行側: くろこげマーカーのコインの前の確かめで、PK1 の組が止める理由にならないこと<br>厳密側では今と同じ HALTED |
| 現行挙動からの差 | 続行側だけ: 今止まる盤面で、2 のあとにまとめて判定して続ける |
| 設計案からの差 | 設計案の候補と同じ推奨。この仕様で、段階を処理の名前で列挙し、未確認だった mid_check_knockout_divergence の条件（2 つ）を読んで、どちらも同じ読み方で決まることを確かめた |
| 推奨 | 2 のあとに 1 回だけ判定（p.323 の手順の番号順で、1 と 2 のあいだに判定の手順がない。今の処理が既にこの読み方なので、新しい処理・乱数の消費がない） |
| 代替案 | 1 のあとにも判定する（手順の途中にきぜつの判定を加える読み方。HP 以上のポケモンが 2 の前に場をはなれ、交代・2 の対象が変わる） |
| 未確認 | 道具の対戦では発生していない（観測 0 局）。組み立てた盤面のテストだけ<br>公式資料に途中の判定の記述がないことの再確認 |

具体化した点:

- **指定した段階（現行コードの処理に対応させた並び）**: ポケモンチェックの始まり（ログ pokemon_check）→ 1 の「指示されたこと」: (1a) くろこげマーカーのコイン（すべて。_flip_char_coins）、(1b) 悪エネルギーの効果（ダメージ・ダメージカウンター。鋼エネルギーの軽減。darkness_penalties）、(1c) くろこげマーカーの「うら」の 20 ダメージ、(1d) きのみ（どうぐ）の回復・効果（その時点の場で、はたらく条件を満たすもの。pokemon_check_berries）→ 2 の「どく」のダメージ（共通の問い合わせ poison_check_amount の量: どくの性質・［ポイズンミスト］・鋼エネルギー） → きぜつの判定（1 回。knocked_by_hp、今有効な最大HP）→ きぜつの処理（サイド・勝敗・交代）→［ずらかる］の確かめ → 3 のねむり → 4 のマヒ → 次の番。
- **この規約が決めること**: (1b)〜(1d) のあと、2 の前に HP 以上になったポケモンについて、1 と 2 のあいだにきぜつを判定しない（場をはなれない）。判定は 2 のあとの 1 回だけ。
- **どく・やけど・ねむり・マーカー・継続効果の順序**: 上の並びのまま（この規約は順序を変えない）。この版のデータに「やけど」状態はなく、くろこげマーカーが 1 の中にある。番の終わりに消える持続する効果は、ポケモンチェックの前に処理する（resolution/flow._end_turn の expire_at_turn_end。今の順）。
- **HP 以上のダメージになったあと、どの処理まで行うか**: 1 の残りの処理と 2 のどくのダメージまで（そのポケモンにもどくのダメージを与え、ログ poison_damage に残す）。3・4 はきぜつの処理のあとなので、きぜつしたポケモンはねむりのコインを投げない（今と同じ）。
- **状態回復・能力の有効・無効との関係**: 判定まで場に残るあいだ、そのポケモンの特殊能力（かがくへんかガスなど）・ついているカードは、今の場の規定のまま（きぜつしたものとして消さない）。2 のどくの量・最大HP は 1 のあとの場で求める（今の処理）。きのみで回復するかは 1 の中の今の処理。
- **両方のきぜつ・勝敗・サイド・サドン・デス**: 2 のあとの判定で両方のプレイヤーのポケモンがきぜつするなら、今の UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT（ダメージの前に止める）のまま。片方だけなら今のきぜつの処理（サイドは利用者の指定のまま）・勝敗（p.311）・交代。サドン・デスへの移り方は今の判定のままで、この規約で新しく作らない。
- **PC-CHECK-SIDE-ORDER との依存**: くろこげマーカーのコインの前の確かめ（すべての結果で 1・2 の確かめ）は、同じ集合のこの規約を使う（この規約があれば、PK1 で止める組がなくなる）。どちらの規約も他方を必要としない。
- **実装**: _pokemon_check_plan の PK1 の分岐（mid_check_knockout_divergence）を、規約があれば呼ばない。今の処理は 2 のあとにまとめて判定する（場に残る読み方）ので、新しい処理は要らない。
- **乱数・公開の情報**: 変えない（判定の時点だけ）。

## 6. S1 の確かめ

| 停止コード | 箇所 | 事例を渡す | 照会の接続 | 備考 |
|---|---|---|---|---|
| `UNRESOLVED_MULLIGAN_COMPENSATION` | `kyuura_engine/engine.py::_deal_opening_hands` | 渡す | 接続済み | 事例（initial-setup・sudden-death-segment）を渡して照会する |
| `UNRESOLVED_PLAY_AS_POKEMON_SETUP` | `kyuura_engine/engine.py::_deal_opening_hands` | 渡す | 接続済み | 準備の停止。事例を渡す |
| `UNRESOLVED_PLAY_AS_POKEMON_SETUP` | `kyuura_engine/engine.py::_place_starting_pokemon` | 渡さない | 未接続 | 拒否の箇所（S1 は拒否の照会を接続していない）。S2a で、新しい事例 #setup-placement を加えてこの 1 か所だけ接続する |
| `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` | `kyuura_engine/procedures.py::halt` | 渡さない | 接続済み | 事例のないコード（場面 1 つ）なので、汎用の停止で場面を特定できる |
| `UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER` | `kyuura_engine/procedures.py::halt` | 渡さない | 接続済み | 同じ |
| `UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT` | `kyuura_engine/procedures.py::halt` | 渡さない | 接続済み | 同じ |
| `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT` | `kyuura_engine/interruption.py::interrupt` | 渡さない | 接続済み | 同じ |
| `UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT` | `kyuura_engine/interruption.py::interrupt` | 渡さない | 接続済み | 同じ |

- **分岐の手前の照会**: S1 の照会（conventions.stop_without_continuation）は止める直前の確かめで、規約があればエンジンの不具合として扱う。S2a の実装では、止める理由を作る分岐の手前に「続行規約を引いて、あれば続ける」照会（案: conventions.continuation_for）を加える。止める直前の確かめはそのまま残し、続行した場面で止めることがないこと（規約のある場面で Halt を作ったらエンジンの不具合）を両側で確かめる。
- **場面を特定できない汎用の停止**: 汎用の停止で事例を特定できないコードは残る（UNRESOLVED_SCRAM_TIMING の #pokemon-check、UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE の #decision-halt など）。S2a の対象のコードはどれも場面を特定できるので、S2a の前提にしない。
- **集合の識別**: 厳密側は CS-KYUURA-CURRENT@1（同じ ID・版・中身のまま）。続行側は新しい集合 CS-KYUURA-PLAY-S2A@1（今の集合の規約 12 件と、続行規約 5 件 @1）。どちらも照合値（集合・規約ごと）で識別し、状態・書き出し（形式 35 の convention_set）・観測に載る。今の集合の版を上げて続行規約を足す案にしない。
- **開発用・部分的な集合**: AGR-RULESET-DEVELOPMENT（規約がそろわない構成は開発用で、完成したプレイ用として扱わない）にしたがい、CS-KYUURA-PLAY-S2A@1 は usage development・completeness halts_at_undecided にする。規約の一部だけの集合は、テスト用の登録表（conventions.Registry）でだけ作り、同梱しない。
- **依存・競合の検査**: S1 の validate が、依存（requires）・競合（conflicts）・同じ場面に 2 つの規約・未実装・承認と区分の組（承認されていない続行規約は通常の集合に入れない）を確かめる。5 規約は互いに requires・conflicts を持たず（関係は related だけ）、対象の場面が重ならない（--check が確かめる）。
- **台帳の事例の行番号**: 台帳の事例の sites（scripts/build_stop_policy_classification.py の手書きの行番号 engine.py:494・515）は、v0.142 で engine.py に行を加えたので今の行と合っていない（この仕様では関数名で参照する。台帳は変えていない。実装の段階で事例を加えるときに直す）。

## 7. 集合の案

- 厳密側: `CS-KYUURA-CURRENT@1`（standard・halts_at_undecided）。変更: なし（同じ ID・版・中身）。
- 続行側: `CS-KYUURA-PLAY-S2A@1`（development・halts_at_undecided）。規約: CS-KYUURA-CURRENT@1 の規約 12 件（利用者の指定 11 件・CB-IMPLEMENTATION-ASSUMPTIONS@1）と、PC-SETUP-MULLIGAN-COUNT@1・PC-SETUP-PLAY-AS-POKEMON@1・PC-CHECK-SIDE-ORDER@1・PC-COIN-COUNT-SHORT@1・PC-CHECK-KO-POINT@1。
- 規約の承認: 続行規約 5 件は、採用されたら layer continuation・approval user_agreed で登録する。CB-IMPLEMENTATION-ASSUMPTIONS は not_approved のまま（承認済みにしない）。
- 照合値に入れるもの: 規約ごとの意味の項目（原則・文・場面・適用条件・除外・数のパラメータ）。参照（文書・研究の記録）は照合値に入れない（S1 の REFERENCE_FIELDS）。
- 呼び方: すべての未決場面で止まらない完成したプレイ用の集合ではない（ほかの未決場面では今の停止コードで止まる）。
- 版: 規約の意味（場面・数え方・時点）を変えたら規約の版を上げ、それを含む集合も新しい版にする。エンジンの不具合の修正は、規約の意味を変えないなら版を上げない（S1 の方針）。

## 8. 判断が残る選択肢

| ID | 規約 | 問い | 推奨 | 代替案 |
|---|---|---|---|---|
| OC-1 | `PC-SETUP-MULLIGAN-COUNT` | 両方の回のあと片方だけが切り直したときの補償の数え方 | 片方だけの回 1 回につき補償 1 回 | 両方の回が一度でもあれば補償なし<br>両方の回も数える（採らない） |
| OC-2 | `PC-SETUP-PLAY-AS-POKEMON` | 準備の配置で化石・人形を選んだときも、この規約で扱うか | 扱う（続行側は規約による拒否。新しい事例 #setup-placement） | 切り直しの判定だけ扱い、配置は今の UnsupportedError のまま |
| OC-3 | `PC-SETUP-PLAY-AS-POKEMON` | 配置の規約による拒否のコード | NOT_BASIC_POKEMON（たねポケモンでないカードの既存の拒否と同じ。理由の文に規約 ID） | 規約による拒否の新しいコード |
| OC-4 | `PC-SETUP-PLAY-AS-POKEMON` | 対象カードを、登録の型（PlayAsPokemon）で識別するか、カードの一覧を規約の中身に入れるか | 登録の型で識別（カードごとに承認を繰り返さない）。今の一覧は参照で、一覧が変わったら --check が見つけ、同じ意味か確かめる | カードの一覧を中身に入れる（カードが増えるたびに規約の版を上げる） |
| OC-5 | `PC-CHECK-SIDE-ORDER` | 両方のねむりのコインの結果を、1 枚ずつすぐ反映するか、両方投げてからまとめて反映するか | 番を終えたプレイヤーのコインをすぐ反映してから相手が投げる（今の処理の並び） | 両方投げてからまとめて反映<br>結果が読み方で変わる盤面だけは続行側でも止める（事例を分ける） |
| OC-6 | `PC-CHECK-SIDE-ORDER` | 両方が投げるときの順番 | 番を終えたプレイヤーから | 番を終えたプレイヤーが選ぶ（決定）<br>次の番のプレイヤーから |
| OC-7 | `PC-CHECK-SIDE-ORDER` | UNRESOLVED_POKEMON_CHECK_BERRY_ORDER（BY1）を対象から除くこと | 除く（効果の種類の順番を含む別の問い） | 両方の側の順番だけの BY1 の事例を分けて対象にする（事例の分け方の調査が要る） |
| OC-8 | `PC-COIN-COUNT-SHORT` | 足りないときの処理 | あるだけ処理する | 効果全体を何もしない |
| OC-9 | `PC-CHECK-KO-POINT` | 1 と 2 のあいだのきぜつの判定 | 2 のあとに 1 回だけ | 1 のあとにも判定する |
| OC-10 | — | 続行側の集合の区分（DEC-PLAY-CONFIG-INCOMPLETE-START の残り） | development・halts_at_undecided で、新しい対戦を始められる（今の S1 の確かめのまま） | 規約がそろうまで続行側の集合で対戦を始めない<br>standard にする（AGR-RULESET-DEVELOPMENT と合わない） |
| OC-11 | — | 規約を当てたことをログに残すか | 残す（convention_applied。続行側の対戦だけ） | 残さない（状態の差だけ。監査・lockstep で規約の当たった歩を特定できない） |

## 9. 実装と検証の段階

5 規約はまとめて採用を判断し、実装は依存に沿って段階に分けます（S2a-1〜S2a-3 は S2a-0 のあとならどの順でもよい。S2a-3 の中は、きぜつ判定の時点 → 両側のコインの順）。

### S2a-0 続行の照会と集合の登録

| 項目 | 内容 |
|---|---|
| 実装対象 | 分岐の手前の照会（案 conventions.continuation_for）<br>続行規約 5 件の登録（内容・固定の照合値・implemented_continuations）<br>集合 CS-KYUURA-PLAY-S2A@1（development）<br>ログ convention_applied と監査<br>台帳の新しい事例 #setup-placement と同梱の場面の一覧の作り直し |
| 前提 | この仕様案の採用<br>DEC-PLAY-CONFIG-INCOMPLETE-START の残り（開発用の集合で対戦を始められるか・止まったときの表示） |
| 共通処理 / カード固有 | 照会・登録・ログ・監査はすべて共通（カード固有の処理はない） / なし |
| 厳密側の不変条件 | 厳密側の集合（既定）で、全体のテスト・lockstep（基点の木と）・旧バッチ・延長戦の道具の結果が今と同じ（意図した差 0） |
| 続行側の完了条件 | 続行規約のどれも、まだ止める分岐を変えない段階で、CS-KYUURA-PLAY-S2A@1 の対戦が厳密側と同じに進む（規約の当たる場面がない対戦） |
| 保存・観測・ログ | 状態の新しい項目はない（集合の識別は S1 の項目）。書き出しの形式は 35 のまま（新しいログの種類 convention_applied だけ。監査の項目表に加える）。観測は convention_set が変わるだけ |
| 回帰テスト | 集合の確かめ（依存・競合・場面の重なり・未実装・承認と区分）<br>厳密側で照会が「規約なし」を返し止め方が今のまま<br>convention_applied の監査（書くべき場面・書いてはいけない場面） |
| 正式な対戦・比べ | 厳密側の lockstep（--corpus all）と旧バッチの比べ |

### S2a-1 準備（切り直しの補償・化石と人形の初手）

| 項目 | 内容 |
|---|---|
| 実装対象 | PC-SETUP-MULLIGAN-COUNT<br>PC-SETUP-PLAY-AS-POKEMON |
| 前提 | S2a-0 |
| 共通処理 / カード固有 | engine._deal_opening_hands の 2 つの分岐・engine._place_starting_pokemon の拒否の手前の照会 / なし（化石・人形は登録の型で識別） |
| 厳密側の不変条件 | 厳密側で、準備の停止・配置の拒否・補償が今と同じ |
| 続行側の完了条件 | 両方 → 片方の切り直しで補償 m 回、化石・人形だけの手札で切り直し、配置の拒否が NOT_BASIC_POKEMON。延長戦の区間でも同じ |
| 保存・観測・ログ | ログに convention_applied と mulligan が増える（続行側）。補償の段階・決定は今と同じ形 |
| 回帰テスト | 各規約の tests_new<br>厳密と続行の lockstep で、差が規約の当たった歩（準備）から始まること |
| 正式な対戦・比べ | 旧バッチの 45 局（UNRESOLVED_MULLIGAN_COMPENSATION 17・UNRESOLVED_PLAY_AS_POKEMON_SETUP 28 の局）を含む全バッチを、両方の集合で |

### S2a-2 コインで決まる枚数の不足

| 項目 | 内容 |
|---|---|
| 実装対象 | PC-COIN-COUNT-SHORT |
| 前提 | S2a-0 |
| 共通処理 / カード固有 | interruption.check_quantity（処理する数を返す照会）・先読みの組・監査・不変条件 / ドライアップ・怪電波マシーンの登録は今の H = N の経路を使う（変えない） |
| 厳密側の不変条件 | 厳密側で、途中停止の記録・在途のカード・観測・書き出しが今と同じ |
| 続行側の完了条件 | H > N で N 枚を処理し、DU1 はワザの終わり、TW1 は番の終わりまで進む。先読み・答えの確かめが通常の完了として数える |
| 保存・観測・ログ | 続行側では途中停止の記録を作らない。ログに convention_applied が増える |
| 回帰テスト | 各規約の tests_new<br>v0.127 の正式な対戦の組（--batch v0.127）を両方の集合で |
| 正式な対戦・比べ | 旧バッチの 13 局（DU1 9・TW1 4 の局）を含む全バッチを、両方の集合で |

### S2a-3 ポケモンチェック（きぜつ判定の時点 → 両側のコイン）

| 項目 | 内容 |
|---|---|
| 実装対象 | PC-CHECK-KO-POINT<br>PC-CHECK-SIDE-ORDER |
| 前提 | S2a-0 |
| 共通処理 / カード固有 | procedures._pokemon_check_plan の PK1 の分岐、procedures.pokemon_check_sleep_and_paralysis・_char_coin_stop の分岐、回復の組の確かめ / なし |
| 厳密側の不変条件 | 厳密側で、ポケモンチェックの停止・ログ・乱数が今と同じ |
| 続行側の完了条件 | PK1 の盤面で 2 のあとに判定、両方のねむり・くろこげマーカーで規約の順に投げて続ける。残る停止（両方のきぜつ・SC1・AL1・MH1 など）は今のコードで止まる |
| 保存・観測・ログ | ログに convention_applied が増える。コインのログの順は今のログの順と同じ |
| 回帰テスト | 各規約の tests_new<br>くろこげマーカーのコインの前の確かめが同じ集合のきぜつ判定の規約を使うこと |
| 正式な対戦・比べ | 旧バッチの 37 局（UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）を含む全バッチを、両方の集合で。番を終えたプレイヤーごとの勝率の差（先攻・後攻の偏り）を記録する |

### S2a-4 一括の計測と文書

| 項目 | 内容 |
|---|---|
| 実装対象 | 5 規約をすべて入れた CS-KYUURA-PLAY-S2A@1 |
| 前提 | S2a-1<br>S2a-2<br>S2a-3 |
| 共通処理 / カード固有 | 道具（tools/existing_effect_games.py・tools/sudden_death_games.py・tools/engine_lockstep.py）に集合を選ぶ引数を加える（道具だけ。エンジンの既定は厳密側のまま） / なし |
| 厳密側の不変条件 | 厳密側の全体のテスト（1 並列・モジュールごとに 1 プロセス）・lockstep・旧バッチ・延長戦が基点と同じ |
| 続行側の完了条件 | 下の計測の結果を、停止コードごとに記録する（完走を保証しない） |
| 保存・観測・ログ | なし（計測だけ） |
| 回帰テスト | 全体のテスト<br>lockstep（厳密 対 厳密: 差 0、厳密 対 続行: 差が最初の convention_applied の歩から始まる） |
| 正式な対戦・比べ | 全 108 バッチ（seed 0〜3。4,356 局）と延長戦の道具を、両方の集合で（組・席・seed は計測の前に決める。選び直さない） |

## 10. 既存の計測との関係

- 基準: docs/play-policy-family-plan.json observation（v0.141 8164194、tools/existing_effect_games.py 全 108 バッチ、seed 0〜3）。4,356 局・止まった局 115。
- 今回の 5 規約は、この計測の止まった 115 局のうち 95 局の停止事例（停止コード UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER 37・UNRESOLVED_PLAY_AS_POKEMON_SETUP 28・UNRESOLVED_MULLIGAN_COMPENSATION 17・UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT 9・UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT 4）に対応する。実装後に 95 局すべてが完走するとは保証しない。
- 残りの 20 局（UNRESOLVED_POISON_MIST_EARLIER_POISON 11・UNRESOLVED_POISON_MIST_SOURCE 7・UNRESOLVED_POISON_CHANGE_ORDER 1・UNSUPPORTED_TRANSFORM_COPIED_POWER 1）は対象外。
- 続けたあと、別の停止（両方のきぜつ・［ポイズンミスト］・SC1・MH1 など、ほかの未決場面・未対応）に着く局がありうる。その停止コードを局ごとに記録する。
- 化石・人形の局は、切り直しのあとに両方 → 片方の切り直し（PC-SETUP-MULLIGAN-COUNT）に当たりうる。5 規約がそろった集合では続くが、そろわない開発用の集合では止まる。
- 続けた局は、対戦の流れ（乱数の位置・手札）が変わるので、そのあとの局の内容を基点の局と比べない（比べるのは、規約の当たった歩までが同じこと）。
- 準備の規約で続けた局は、基点では準備で止まっていたので、対戦の中身すべてが新しい（道具の方策の予期しない拒否・内部エラーが出れば、規約と別の不具合として記録する）。
- 実装後に記録するもの: 局ごとの終わり方（game_over・halted とその停止コード・interrupted・unexpected_rejection・internal_error）を、両方の集合で、規約ごとに当たった局の数・回数（convention_applied）、厳密 対 続行の lockstep で、最初の差の歩が convention_applied の歩であること、PC-CHECK-SIDE-ORDER の当たった局の、番を終えたプレイヤーごと・先攻後攻ごとの勝ち負け（基準の値は設けず、記録する）。

## 11. 確かめたこと（実行した確認と、読んだだけの確認）

実行した確認:

- python scripts/build_play_policy_s2a_spec.py --check: problems=0（終了コード 0）。
- わざと壊した仕様案（存在しない場面・対象の漏れ・規約の重なり・同じ規約の対象の除外・理由のない他の規約の対象の除外・存在しないテスト・実装箇所・研究の記録・判断事項・依存・設計案の候補・観測の数・計測の数・段階の漏れ・具体的な仕様の承認・規約の承認）を --check が見つける: tests/test_play_policy_s2a_spec.py 8 テスト OK。
- 停止の方針の台帳・共通規約の設計案・同梱の規約集合の記録の --check: どれも終了コード 0（台帳・設計案・同梱の記録は変えていない）。
- 主張の確認に使った既存のテスト（モジュールごとに 1 プロセス。どれも終了コード 0・失敗 0）: test_setup 15・test_fossil_hidden_info_v0_47 55・test_sudden_death_v0_134 28・test_rocket_snorlax_v0_17b 33・test_confusion 29・test_pokemon_check_v0_3b 22・test_marker_check_field_reset_v0_91 44・test_shared_checks_pokemon_reuse_v0_79 45・test_neo_trainer_components_v0_80 52・test_deferred_shortage_user_promos_v0_127 33・test_conventions_v0_142 31・test_stop_policy_classification 13・test_play_policy_family_plan 19（計 419）と、新しい test_play_policy_s2a_spec 8。
- ruff 0.17.2（v0.142 と同じ版・設定）: 新しい 2 ファイルは指摘 0・抑制（noqa）なし。リポジトリ全体の指摘の数は v0.142 と同じ 492。

読んだだけの確認・走らせていないもの:

- 5 章の「コードで確かめた」「コードを読んで確かめた」は、どれもコードを読んだだけ（続行の処理は実装していないので実行していない）。
- 既存のテストが確かめるのは今の挙動（厳密側）だけ。続行側の主張（補償の数・切り直し・コインの順番・あるだけ処理・判定の時点）は、実装の段階の新しいテストで確かめる。
- 全体の対戦テスト・lockstep・旧バッチは走らせていない（エンジンを変えていないので。調査と設計だけ）。

## 12. 未確認

- 5 規約とも、公式資料に記述がないことの再確認はしていない（研究上の未解決は未解決のまま。続行規約は研究上の解決ではない）。
- kyuura の記録は、固定した研究基準の写し・エンジンの記録の参照だけ（kyuura を読み直していない）。
- コードの確かめは読んだだけ（実行して確かめたのは --check の参照と、既存のテストの実行。11 章）。
- PC-CHECK-SIDE-ORDER: 先の回復が後のコインの枚数・回復の止め方を変える盤面の到達可能性、先攻・後攻の偏り。
- PC-CHECK-KO-POINT: 道具の対戦で 0 局（組み立てた盤面だけ）。
- 続けたあとにどの停止へ着くか（局の数）は、実装と計測のあとでしか分からない。

## 13. 採用のあとの経過（v0.143）

- 採用: `user_agreed`（2026-11-04）。利用者の指示「5規約をまとめて採用し、S2a-0〜4を一つの実装タスクとして進める案を採用します。」と、その依頼の採用仕様。この指示と、その依頼に書いた具体的な採用仕様（5 規約の対象・処理・除外）。続行側の開発用の部分的な集合の規約の採用で、公式の裁定・エラッタ・kyuura の研究上の解決ではない。厳密側の集合・ほかの未決の場面・未承認の仮定は変えない。
- 実装: 版 0.143.0（docs/play-policy-s2a-v0.143.md・作業ブランチ `claude/play-policy-s2a-impl`）。集合 `CS-KYUURA-PLAY-S2A@1`（開発用・halts_at_undecided）。
- 進め方の承認（2 章）と、具体的な続行仕様の採用（この章）は別の記録です。2 章の「具体的な続行仕様の承認: not_approved」は提案の時点の記録で、書き換えていません。

| 選択肢 | 採用 |
|---|---|
| OC-1 | 推奨のとおり（片方だけの回 1 回につき補償 1 回） |
| OC-2 | 推奨のとおり（配置も扱う。新しい事例 #setup-placement） |
| OC-3 | 推奨のとおり（NOT_BASIC_POKEMON。既存の拒否と同じコードで、理由の文に規約 ID） |
| OC-4 | 推奨のとおり（登録の型で識別。今の対象の一覧は照合だけ） |
| OC-5 | 推奨のとおり（1 枚ずつすぐ反映） |
| OC-6 | 推奨のとおり（番を終えたプレイヤーから） |
| OC-7 | 推奨のとおり（BY1 は除く） |
| OC-8 | 推奨のとおり（あるだけ処理） |
| OC-9 | 推奨のとおり（2 のあとに 1 回だけ） |
| OC-10 | development・halts_at_undecided の集合で新しい対戦を始める（採用の指示） |
| OC-11 | 推奨のとおり（convention_applied を残す。続行側の対戦だけ） |

仕様案からの差:

- PC-CHECK-SIDE-ORDER: ねむりの回復の結果のすべての組の確かめ（4 通り）は、規約そのものではなく技術的な安全の確かめとして区別した（採用仕様）。止める組があればコインの前にその停止コードで止める。両方の組だけで止まる盤面は作れていない（到達可能性は未確認）。
- PC-CHECK-KO-POINT: 仕様案は「規約があれば違いの判定を呼ばない」としていた。実装は違いの判定を呼び、厳密側が止める場面だけを規約の適用として記録する（処理は同じ）。また、場に残る読み方で 2 のあとにきぜつさせると、そのきぜつの処理で受け付けられない状態（TK1・SC2・MH1・決められない姿）になる場面は、規約を当てずにダメージの前にその停止コードで止める（保守的な制限。仕様案の「違いを返す 2 つの条件はどちらも場に残る読み方で決まる」は、きぜつの処理のあとの停止を見ていなかった）。
- PC-COIN-COUNT-SHORT: 仕様案のとおり。チェック地点（interruption.check_quantity）は状態を受け取り、処理する数を返す形にした（呼ぶ側は返した数を処理する）。
- PC-SETUP-MULLIGAN-COUNT・PC-SETUP-PLAY-AS-POKEMON: 仕様案のとおり。
- 台帳の事例の行番号: 手書きをやめ、作成スクリプトが今のコードの止める分岐の行から求める（仕様案 6 章の記録の不具合の修正）。
