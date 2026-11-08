# v0.174: 本人のうらのバトル場のポケモンのにげるの入力（R-5 の P6）

[R-5 の監査](legal-actions-r5-audit.md) 5 章の提案 P6 を、エンジンの側の 1 単位として実装しました。公開の情報から安全に作れる入力を API に加える作業で、ゲームの合法性・裁定・
エンジンのコマンドの処理は変えていません。

## 1. 採用の記録

- 採用: 利用者の指示（2026-11-09「R-5監査で提案されたP6（本人のうらのバトル場のポケモンのにげる入力）の補完を採用します。」）
- 範囲: `legal_actions._retreat_candidate` の、本人のバトル場のポケモンがうら（マチスの秘策）の分岐だけ。GUI・renderer・kyuura・カードデータ・固定デッキ・規約集合・裁定・識別の方式・
  検証用 AI の道具は変えていない
- 位置づけ: **進行不能を解消する修正ではない**。P6 は v0.173.0 でも進行を止めない（同じ番のほかの操作・番を終えるは示される）。うらのままにげる操作（ルール上できる。エンジンは
  おもてにしてから確かめる）を、API から選べるようにするだけ
- 監査の結論の限定: 監査の「決定待ちで止まるのは C 群だけ」は、監査で確かめた登録・経路の範囲での結論。P2（見えないカードが選べるものにある実行時の確かめ）の通常の到達は未確認で、
  届く経路がないとは断定していない。今回は P2 を再監査していない

## 2. 入力契約（実装の前に決めた）

### 2.1 候補

| 項目 | おもてのにげる（変えない） | うらのバトル場のにげる（v0.173.0） | うらのバトル場のにげる（v0.174.0） |
|---|---|---|---|
| `input_disclosure` | `confirmed` | `unconfirmed`（入力を返さない。R-5） | `confirmed` |
| `processability`・`reasons` | 確かめの結果 | `unverified`・`["face_down_reveal_not_evaluated"]` | 同じ（変えない） |
| `guarantees` | `GUARANTEE_TURN_ACTION` | `GUARANTEE_TURN_ACTION`（入力の検査で `check_retreat` を呼ぶ、と書いてあり、うらでは当たらなかった） | `GUARANTEE_FACE_DOWN_RETREAT`（同じ 4 つの項目。確かめを呼ばないことを書く） |
| `choices_format` | `[入れ替える控えの番号, トラッシュするエネルギーの番号, ...]` | 同じ | 同じ |

本人だけが知る本当のカード（カード ID・名前・にげるエネルギー・タイプ）は、候補・理由・保証・入力のどこにも書かない。相手・観戦者の応答にはにげるの候補そのものがない（番のプレイヤーだけ）。

### 2.2 入力の段

| 段 | おもてのにげる | うらのバトル場のにげる（v0.174.0） |
|---|---|---|
| 1（`role` `new_active`・`meaning` `pokemon`） | 本人のベンチのポケモン（公開。うらの控えは `face_down`）。`count` 1〜1。各選べるものに `eligible`・`processability`・`reasons` | 同じ形。各選べるものは `eligible` 真・`processability` `unverified`・`reasons` `["face_down_reveal_not_evaluated"]` |
| 2（`role` `discard`・`meaning` `card`） | ついているカード。`count` 0〜枚数。`distinct`・`order` `significant`・`order_preserved`。`total_units`（にげるエネルギーの範囲）と、選べるものごとの `units` | ついているカード（公開）。`count` 0〜枚数。`distinct`・`order` `significant`・`order_preserved`。**`total_units`・`units` を省き**、かわりに `cost_evaluation` を置く。各選べるものに `card`・`card_id`・`special`・`eligible` 真・`processability` `unverified`・`reasons` |

新しい項目 `cost_evaluation`（段 2 だけ。オブジェクト）:

```json
{"status": "not_evaluated", "reason": "face_down_reveal_not_evaluated", "omitted": ["total_units", "units"]}
```

- `status` は今は `not_evaluated` だけ。`reason` は候補の理由と同じ語彙（`REASON_FACE_DOWN`）。`omitted` は、この段で省いた項目の名前（段の `total_units` と、選べるものの `units`）
- **省略できる条件**: `total_units`・`units` を省くのは、`cost_evaluation` があり、`status` が `not_evaluated` の段だけ。`cost_evaluation` のない段（おもてのにげる）は今までどおり
  `total_units` とすべての `units` がある。`cost_evaluation` も `total_units` もないにげるの段は、契約の外（クライアントは不明な応答として止める）
- **クライアントが計算してはいけない値**: にげるエネルギー（費用）・カードごとのエネルギーの個数・選んだカードで足りるか。0 と見なさない。うらのポケモンの本当のカード（本人の観測の
  `real`）から求めない（費用・個数は、場の効果・持ち主のタイプによる読み方・特殊エネルギーで変わり、エンジンがおもてにしてから決める）
- **入力の並びと意味**: `choices` は `[段 1 の番号, 段 2 の番号, ...]`。1 つめが入れ替える控え、残りがトラッシュするカードで、送った並びがトラッシュの並び（`order` `significant`。U7 は
  並びを変えない）。段 2 は 0 枚も選べる
- **`eligible`・`processability` の意味**: `eligible` 真は「入力として選べる（形の上で受け付ける）」だけ。`processability` `unverified` は「候補の作成・入力の検査で受理を確かめていない。
  送ればエンジンがおもてにしてから決める」。どちらも、にげられる・受理されるという保証ではない

### 2.3 check と submit

- `check`: 公開の情報と入力契約から確かめられる構造だけを検査する。選べるものの番号があること、1 つめが段 1・残りが段 2、段 2 の重なりがないこと（したがって数は 0〜枚数）。控えと
  エネルギーは候補が持つ番号（候補を作ったときの控えのいちばん上のカード・ついているカード）だけを引く。エンジンの確かめ（`check_retreat`）・状態の複製の上でおもてにして試すことは
  しない。形が合えば `valid` 真。**`valid` 真は、にげられる・受理されるという保証ではない**
- `submit`: 既存の `Retreat(actor, トラッシュするカード（選んだ順）, 控え)` をそのまま送る。エンジンは番・決定待ちでないことを確かめたあと、このポケモンをおもてにし（`_reveal_for_action`）、
  本当のカードが「たねポケモン」ならふつうに確かめる（受け付けなければコマンドごと拒否。状態・乱数・ログはもどり、おもてにしたことも公開しない。拒否は送った本人だけ）。「たねポケモン」
  でなければ、ついているカードといっしょにトラッシュして受理する（全員に公開）。受理で取っ手はすべて失効する（今までどおり）。FD1 などの停止は変えていない

### 2.4 形式の版

`kyuura_legal_actions_format`・クライアント API の `format` は 1 のまま。既存の運用（U7-5g の 3 段目 `energy2`・`options_by_path`・coverage の residual は、既存の項目の意味を変えない
追加として形式 1 のまま加えた）に合わせる。既存の項目（`total_units`・`units`）の意味は変えず、うらのバトル場のにげるの段で省き、省いたことを新しい項目で示す。ただし、項目の追加だけを
根拠に古いクライアントが正しく動くとはしない（5 章）。
