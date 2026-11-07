# v0.163: 合法手 API の準備の操作とホストの操作（U7-2）

U7 の入口で、対戦の準備（初期配置・切り直しの補償の引く枚数）と、対戦全体のホストの操作（ジャンケンの結果・延長戦の開始）を扱えるようにしました。`kyuura_engine` の版は 0.163.0 です。既存のコマンドの意味・ジャンケンの方式・先攻の決め方・補償の数と時点・続行規約・停止の扱いは変えていません。

準備とホストの操作に対応しても、**番の候補は部分実装**です（番を終えるだけ。ほかの 12 種類は `not_covered_kinds`。U7-3 以後）。

## 採用の記録

<!-- generated:setup-adoption begin -->
- `ADOPT-U7-2`（2026-11-07・利用者）: U7-2（準備の操作とホストの操作。初期配置・切り直しの補償の引く枚数・ジャンケンの結果・延長戦の開始）の実装だけ。既存のコマンドの意味・ジャンケンの方式・先攻の決め方・補償の数と時点・続行規約・停止の扱いは変えない。U7-3 以後の操作の種類・識別の方式の移行・GUI・AI の承認ではない。実装: v0.163（docs/legal-actions-u7-2.md）
  - 方針:
    - プレイヤーが行う操作（本人の初期配置・本人の補償の引く枚数）と、対戦全体のホストの操作（ジャンケンの結果・延長戦の開始）を分ける
    - ホストの操作の入口は信頼されたアプリケーションだけが持ち、プレイヤーの入口から移れない。入口の所有と権限の確かめはホストするアプリケーションの責任
    - U7-1 の取っ手・結果・coverage の契約を使う（ホストの取っ手とプレイヤーの取っ手を取り違えない）
    - 化石・人形の未裁定・規約による拒否を、候補から消さずゲーム上の禁止と区別する
  - 判断事項: なし（新しく採用した判断事項はない）
  - 実装単位: U7-2
<!-- generated:setup-adoption end -->

## 1. 既存のコマンドの意味と送る主体（コードで確かめた）

| コマンド | 送る主体 | 入力と制約（エンジンの確かめ） | 次の段階・停止 |
|---|---|---|---|
| `PlaceStartingPokemon(player, active, bench)` | 各プレイヤー（両方が同じ段階で、順は問わない） | 手札からバトル場に 1 枚・ベンチに 0〜`rules.max_setup_bench` 枚。重なりは不可（`DUPLICATE_CARD`）。たねポケモン・ベイビィポケモンだけ（`NOT_BASIC_POKEMON`）。化石・人形は、状態の規約集合の続行規約があれば「たねポケモンとして数えない」拒否（`NOT_BASIC_POKEMON`）、なければ未裁定の停止（`PLAY_AS_POKEMON_SETUP_CODE`。拒否として返り、状態は変わらない） | 両方が置いたらサイドを置き、補償があれば補償、なければ先攻を決める段階（止まる処理はない） |
| `DrawMulliganCards(player, count)` | 補償が残るプレイヤー（相手の切り直しの回数ぶん） | 1 回ごとに 0〜`rules.mulligan_draw_max_per_mulligan` 枚、山札の枚数まで | 補償がなくなれば先攻を決める段階（止まる処理はない） |
| `ReportJankenResult(winner)` | ホスト（ジャンケンはエンジンの外の出来事。エンジンは乱数で決めず、勝者を受け取る） | 先攻を決める段階・勝者は 0 か 1 | 勝者を先攻にし、場のポケモンを表にして勝者の番が始まる |
| `StartSuddenDeath()` | ホスト（player を持たない。どちらかのプレイヤーの選択ではない） | サドン・デスに移った状態だけ。整合の確かめ（不変条件・最初のデッキの復元）は処理できない結果（failed） | 区間を記録して最初のデッキにもどし、乱数を今の状態から続けて準備をやり直す。補償・化石の手札で止まりうる（通常の準備と同じ停止） |

切り直し（手札にたねポケモンがないときの引き直し）と、その回数の数え方は `new_game`・延長戦の準備が行い、プレイヤーの操作ではありません（U7 は回数を作り直さない）。補償の数は状態の `mulligan_draws_remaining`（相手の切り直しの回数。ログの公開の情報）をそのまま示します。

## 2. 公開の API

| 入口 | 持つ人 | 内容 |
|---|---|---|
| `ActionHost.session(actor)` | ホストが本人（0・1）に渡す | プレイヤーの入口（U7-1 と同じ）。初期配置・補償の候補が加わった |
| `ActionHost.host_session()` | 信頼されたアプリケーションだけ | ホストの操作の入口 `HostSession`（`candidates`・`inputs`・`check`・`submit` は同じ形。主体は `host`）。ジャンケンの結果・延長戦の開始だけを候補にし、プレイヤーの決定・操作は出さない |

- **権限**: ホストの入口の所有と、その入口を呼べる人の権限の確かめは、ホストするアプリケーションの責任です（ライブラリは認証をしない）。プレイヤーの入口からホストの入口へ移る方法はありません。主体は入口を作ったときの窓口に固定され、入口の属性（`_actor`）を書きかえても主体は変わりません（テスト）。Python の型だけでは、閉包の中の参照まで隠せないので、信頼できないコードと同じプロセスで動かさないのはホストの責任です
- **取っ手**: ホストの取っ手は主体 `host` に結びつき、プレイヤーの取っ手と取り違えると `CANDIDATES_WRONG_ACTOR` です。保持の上限・受理による全取っ手の失効・拒否で他の主体の取っ手を失効させないこと・差し替え・復元・作り直しによる失効は U7-1 と同じ
- **結果**: ホストの送信の結果 `ActionResult.view` はホストだけへの定型の診断 `HostNotice`（v0.164 で直した。v0.163 は全員向けの知らせ `CommandResult.view_for(None)` を使い、拒否では `None` になってホストが理由を受け取れなかった。[client-api-v0.164.md](client-api-v0.164.md)）。`CommandResult` そのものは `on_result(actor="host", result)` でホストだけが受け取る（通常の閲覧者へそのまま送らない）

## 3. 対応範囲

| 種類 | 主体 | 入力 | 処理可能性 | 完全性 |
|---|---|---|---|---|
| `place_starting` | プレイヤー（まだ置いていない人） | 2 段（バトル場 1 枚、ベンチ 0〜上限。段をまたいで重ならない）。選べるものは本人の手札のたねポケモン・ベイビィポケモンと、化石・人形（区分つき）。送るのは `[バトル場, ベンチ, …]`（ベンチは選んだ順に場に並ぶ。並びに意味がある） | `supported`（入力の検査がエンジンの受理の条件と同じ述語と規約の照会を使う） | `complete`（その段階の本人の操作） |
| `mulligan_draw` | 補償が残るプレイヤー | 枚数 1 つ（0〜上限・山札の枚数まで）。残りの回数 `remaining` | `supported` | `complete` |
| `report_janken` | ホスト | 勝者 1 つ（0 か 1） | `may_stop_later`（番の始めの処理は評価していない） | `complete`（ホストの操作） |
| `start_sudden_death` | ホスト | なし | `may_stop_later`（延長戦の準備で止まりうる） | `complete` |

化石・人形（`play_as_pokemon_in_hand`）は候補から消さず、選べるものの `placement` で区別します:

- `excluded_by_convention`: 状態の規約集合の続行規約（`conventions.continuation_for`。モードの名前・カードの ID で分けない）が、たねポケモンとして数えない（規約による拒否。ゲーム上の未裁定ではない）。`convention` に規約の ID と版
- `stops`: 続行規約がない（選ぶと未裁定で止める。`processability` は診断のコード表の分類で `unresolved_ruling`）
- どちらも `eligible` が偽で、送ろうとするとホストの段で `CANDIDATE_NOT_EXECUTABLE`（エンジンに送らない。状態は変わらない）

3 つの規約集合では、`CS-KYUURA-CURRENT@1` が `stops`、`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1` が `excluded_by_convention`（どちらも化石・人形の初手の続行規約を持つ）でした（テストは規約の照会の結果と照らし、集合の名前で分けていない）。

## 4. 情報境界と処理可能性

- 初期配置の選べるものは本人の手札（本人に見える）だけ。相手の手札・山札の並び・サイド（準備の途中でまだ置いていない）を読まない。相手の入口には本人の手札の uid を出さない
- 補償の上限は公開の値（ルールの上限・山札の枚数）と残りの回数（相手の切り直しの回数。公開のログ）だけ
- ホストの候補はプレイヤーの手札・選択を含まない
- 候補の取得・入力の取得・入力の検査で、状態・乱数・ログを変えない。候補のために `apply_command` を試さない。送信は U2 のアダプタ
- 山札の並びだけが違う双子で、プレイヤー 2 人とホストの候補・入力・入力の検査・不正な問い合わせの答えが同じ（取っ手の文字列は比べない）
- 処理可能性（`supported`・`may_stop_later`・`unresolved_ruling` など）と入力を示して安全か（`input_disclosure`）は U7-1 と同じく別の軸

## 5. 利用例

```python
from kyuura_engine.legal_actions import ActionHost

host, start = ActionHost.start(deck0, deck1, seed, on_result=publish)  # ホスト（信頼されたアプリケーション）
alice, bob = host.session(0), host.session(1)                          # 本人の入口（本人だけに渡す）
admin = host.host_session()                                             # ホストの入口（クライアントに渡さない）

# 初期配置（2 段。1 つめがバトル場、残りがベンチ。ベンチは選んだ順）
r = alice.candidates()
stages = alice.inputs(r["game"], r["revision"], "c1")["stages"]
eligible = [o["id"] for o in stages[0]["options"] if o["eligible"]]     # 化石・人形は eligible が偽（placement が理由）
alice.submit(r["game"], r["revision"], "c1", eligible[:3])

# 補償の引く枚数（相手の切り直し 1 回ぶん。0 枚も選べる）
r = bob.candidates()
stage = bob.inputs(r["game"], r["revision"], "c1")["stages"][0]       # {"range": {"min": 0, "max": 2}, "remaining": 1, ...}
bob.submit(r["game"], r["revision"], "c1", [stage["range"]["max"]])

# ジャンケンの結果（ホストだけ。エンジンは乱数で決めない）
r = admin.candidates()                                                  # candidates: [{"kind": "report_janken", ...}]
admin.submit(r["game"], r["revision"], "c1", [winner])

# 番へ（U7-1 の候補）
r = host.session(winner).candidates()                                   # candidates: [{"kind": "end_turn", ...}]、coverage は partial

# 延長戦の開始（サドン・デスに移ったとき。ホストだけ）
r = admin.candidates()                                                  # candidates: [{"kind": "start_sudden_death", "processability": "may_stop_later"}]
result = admin.submit(r["game"], r["revision"], "c1")                   # 準備で止まれば result.view.status == "halted"

# 古い取っ手は拒否される → 取り直す
old = admin.submit(r["game"], r["revision"], "c1")                      # refusal.code == "CANDIDATES_STALE"
```

表示の例: `excluded_by_convention` は「この規約集合では、この化石・人形を最初のポケモンとして出せません（規約 …）」、`stops` は「この化石・人形を最初のポケモンとして出せるかは記録で決まらないため、今は処理できません（ゲーム上の禁止ではありません）」。

## 6. 決定の入力の監査の保守ルール

v0.162 の出し方の一覧（`scripts/legal_actions_decision_sites.py` の `AUDIT`）は、出し方の組（種類・ファイル・クラス・関数）が加わる・消えると `--check` が失敗しますが、**既にある出し方の選べるもの・制約・情報源・回答の処理が変わったことまでは見つけません**。次を保守のルールにします（[legal-actions-decision-audit.md](legal-actions-decision-audit.md) 6.1 節にも書いた）:

- 決定の選べるもの・選ぶと止める選択・選ぶ数・情報源・回答の適用を変えたら、その出し方を再監査する（判定を `AUDIT` に書き直す）
- 種類の名前や出し方の組の一致だけで、安全性と答えの並びの分類を引き継がない
- 変更の影響を受ける共通処理（`zones`・`effects` の補助関数など）と、それを呼ぶすべての出し方を確かめる

U7-2 は新しい決定を出す箇所・情報源を加えていない（`AUDIT` は変わらない。走査の照らしは通る）。答えの並びが未確認の 12 種類（39 種類の外）は、入力の並びを保ったまま別の確認の項目として残す。

## 7. 検証（限定）

- `tests/test_legal_actions_u7_2.py`: new_game から U7 だけで準備を終えて番へ（直接の送信と同じ状態・乱数・ログ・観測・診断。3 つの規約集合）、たねとベイビィの配置・バトル場とベンチの制約・重なり・不正な選択・ベンチの並び、化石の扱い（3 つの規約集合）、補償の 0 枚・上限・範囲の外・補償を受けない人、準備で止まる対戦、ジャンケンの段階・権限・入力・勝者、プレイヤーの入口から昇格できないこと、延長戦の開始とその準備・準備での停止、受理・拒否・内部エラーと取っ手、古い・別の対戦・別の主体の取っ手、取得での不変、双子
- U7-1 の決定への回答と番を終える操作のテスト（`tests/test_legal_actions_u7_1.py`・`tests/test_legal_actions_decision_audit.py`）は、準備が対応した種類になったことに合わせて期待を直し、ほかはそのまま通る
- 停止の方針の台帳（`docs/stop-policy-classification.json`）は、停止のコードに触れるテストの一覧を数える。新しいテストが化石・人形の初手の停止のコードに触れたので、`scripts/build_stop_policy_classification.py --write` で作り直した（変わったのはその項目のテストの一覧と行の数だけ。分類・停止のコードは同じ）
- 全体のテスト・状態の監査・lockstep・大きな対戦は実行していない

## 8. 最小のアダプタと U7-3 以後への引き継ぎ

- U7 の入口だけで、対戦の開始から番の始めまで進められる（番の中は番を終えるだけ）。最小のアダプタ（GUI・単純な AI の接続の確かめ）は、準備・決定・番を終えるの範囲で U7-3 の前に試せる
- 番の通常の操作（ベンチに出す・エネルギーをつける・進化・にげる・ワザ・トレーナー・パワーなど）は U7-3〜U7-5
- ホストの入口は延長戦の開始とジャンケンの結果だけ。`operation_id` による重複の排除は未実装の別の契約
