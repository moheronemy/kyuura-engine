# U7-4: ワザの候補と宣言の入力（v0.166）

合法手 API（`kyuura_engine.legal_actions`）とクライアント向けのアダプタ（`kyuura_engine.client_api`。契約 `kyuura-client-api`・形式の版 1）に、自分の番のワザの宣言（既存の
`UseAttack`）の候補・宣言の入力・入力の検査・送信を加えた版です。トレーナー・特殊能力・スタジアムなどの新しい操作（U7-5）、GUI・renderer は変えていません。エンジンの受け付ける
条件・宣言の前の先読み・状態の移り変わり・乱数・ログ・観測・続行規約・停止の扱い・コピーの範囲・裁定は変えていません。3 つの規約集合（`CS-KYUURA-CURRENT@1`・
`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）の ID・版・中身・照合値、kyuura、カードの写し、固定デッキ、過去の参照データは変えていません。

採用の記録（`scripts/build_legal_actions_api_design.py` の `ADOPTION_U7_4` から作る）:

<!-- generated:attack-adoption begin -->
- `ADOPT-U7-4`（2026-11-08・利用者）: U7-4（ワザの候補と宣言の入力。既存の UseAttack）の実装だけ。既存のコマンドの意味・受け付ける条件・宣言の前の先読み・状態の移り変わり・乱数・ログ・観測・続行規約・停止の扱い・コピーの範囲・裁定は変えない。トレーナー・特殊能力・スタジアムなど（U7-5）・識別の方式の移行・GUI・renderer の変更の承認ではない。実装: v0.166（docs/legal-actions-u7-4.md）
  - 方針:
    - 範囲はコマンドで決める（UseAttack の全項目: attack_index・card・stadium_coin・attack_power・with_power・with_powers）。ワザの名前・カード ID で範囲・処理を分けない
    - 選べるワザは effects.available_attacks（今の姿・コピー・変身・許可で使えるワザ。公開の場から決まる）。宣言の確かめは resolution.flow.check_use_attack（宣言の前の先読みの前の部分を同じ順番・同じコード・同じ文のまま関数にしたもの）だけを使い、apply_command・宣言の前の先読みを試さない
    - ワザの対象・トラッシュするエネルギー・山札から選ぶカード・写すワザは受理のあとの既存の決定で答える（宣言の前へ移さない）。コインの結果を選ばせない
    - ゲーム上宣言できないワザ・組は出さず、未裁定・未対応は消さずに実行できない区分で示す。宣言の前の先読みと受理のあとを評価していないので、ワザの候補を supported にしない
    - U7-1〜U7-3 の取っ手・結果・coverage・client_api の契約を使う（番の候補は partial）
  - 判断事項: なし（新しく採用した判断事項はない）
  - 実装単位: U7-4
<!-- generated:attack-adoption end -->

## 1. 基本の契約

- 候補は本人の知識と公開の情報だけから作る: 自分のバトル場のポケモン・場の公開のカード・印刷のワザの定義（`effects.available_attacks`）。相手のうらのカードは定義を読まない
  （エンジンがうらの定義を返す。［ものまね］はうらの対戦ポケモンからワザを借りない）
- 宣言の確かめは `resolution.flow.check_use_attack`（エンジンの `_use_attack` の、宣言の前の先読みより前の部分を、同じ順番・同じコード・同じ文のまま関数にしたもの。状態・乱数・
  ログを変えない）だけを使う。`apply_command`・宣言の前の先読み（`resolution.preflight`）は候補の作成・`inputs`・`check` で呼ばない
- ゲーム上宣言できないワザ・組（`IllegalActionError`）は出さない。未裁定・未対応（`UnsupportedError`）は消さずに、実行できない区分で示す
- 候補に載ることは、宣言の受理もワザ全体の完走も保証しない。最終の判定は `apply_command`（包んだ対戦の `submit`）
- 番の候補の `coverage.completeness` は `partial` のまま（トレーナー・特殊能力・スタジアムなど 7 種類が `not_covered_kinds`）

## 2. 宣言のコマンドと、すべての入力の経路の分類

`UseAttack`（`kyuura_engine/commands.py`）の全項目と、ワザの宣言からワザの終わりまでの入力の経路です。

| 項目・経路 | 意味 | 分類 | U7-4 の扱い |
|---|---|---|---|
| `player` | 宣言するプレイヤー | — | ホストが結びつけた操作主体（要求に書かせない） |
| `attack_index`・`card` | ワザ（印刷したカードの uid と位置。`card` が None なら今の姿のカード） | 宣言時に必須 | 1 段目の選べるもの（`available_attacks` の並び）。名前・一覧の位置では指さない |
| `stadium_coin` | クチバシティジムのコインを投げる（v0.57） | 宣言時に任意 | 2 段目の `addon: stadium_coin`。場のスタジアムと「マチスのポケモン」はエンジンの確かめ |
| `attack_power` | ワザを使うポケモン自身の、ワザといっしょに使える特殊能力（［すいりょくはつでん］。v0.88） | 宣言時に任意 | 2 段目の `addon: attack_power` |
| `with_power`・`with_powers` | 自分の場のポケモンの、ワザといっしょに使う特殊能力（［XXXXX］・［ANGER］。v0.118・v0.122） | 宣言時に任意（並びの順に宣言する） | 2 段目の `addon: with_power`（場のポケモンごと）。1 つなら `with_power`、2 つ以上なら選んだ順の `with_powers` で送る |
| ワザの対象（相手の控え・自分のポケモンなど） | ワザの効果の対象 | 宣言後の決定 | 受理のあとの既存の決定（`select_pokemon` など）に `answer_decision` で答える |
| トラッシュするエネルギー（ひのこ・ほのおのうずなど） | 説明が書くトラッシュ | 宣言後の決定 | 既存の決定（`discard_energy`）。宣言の前に聞かない |
| 山札から選ぶカード（なかまをよぶ・しんかのほうしなど） | 山札の検索 | 宣言後の決定 | 既存の決定（`SEARCH_DECK` など。始まった検索の本人の選択肢だけ実際の山札による） |
| 写すワザ（ゆびをふる・サイコデュープなど） | 相手のワザを選ぶ | 宣言後の決定 | 既存の決定（`select_opponent_attack`・`select_attack`） |
| コイン・こんらんのコイン | 乱数 | 宣言後（エンジンが投げる） | 入力にしない（結果を選ばせない） |
| 任意の効果（「のぞむなら」） | 選ぶかどうか | 宣言後の決定 | 既存の決定（`optional_coin` など。0 個・辞退は決定の契約どおり） |

ワザの候補の 1 段目に出すのは、バトル場のポケモンが今持つワザ（`available_attacks` の `route`）です。

| `route` | 持ち方 | 例 |
|---|---|---|
| `form` | 今の姿のカードのワザ（［へんしん］・「ばける」の姿を含む。`card` は今の姿のカード） | ヒトカゲ・［へんしん］したメタモン（相手の対戦ポケモンのカードの uid） |
| `recall` | 「思い出させる」で使う進化前のワザ | RC2〜RC4 の場面は選ぶと止める（`unresolved_ruling`） |
| `psylink` | ［サイコリンク］で持つ、自分の場の「超」ポケモンのワザ（`provider`） | ナツメのフーディン |
| `prehistoric`・`puppet`・`mimic` | 許可で使えるワザ（`grantors`。［にんぎょうつかい］は `payer`） | プテラ・スリーパー・ウソッキー |

コピー・変身のワザで選ぶと止めるもの（VA1・SQ1・PE1・VP1・RC2〜RC4・VS1 など、`AttackOption.problem`）は、`checks.attack_request` がほかの確かめのあとに `UnsupportedError` で
止めるので、選べるものとして示し、実行できない区分にします（範囲を新しく決めていません）。

## 3. 確かめの境界（A〜D）

| 区分 | 条件 | どこで確かめるか |
|---|---|---|
| A. 公開の情報と本人の知識だけで決まる | 番・段階・ねむり・マヒ・ワザを使えない効果（しっぽをふる・すごむ・［いあつ］・あわあわ）・1 回しか使えないワザ・必要なエネルギー（色と個数）・説明の使う条件（ベンチの空き・ダメージカウンター・マーカー・相手の控え）・効果の登録・要素の並び・TE2・選ぶと止めるワザ（`option.problem`） | 候補の作成（ワザごとに `check_use_attack`） |
| B. 入力がそろって初めて決まる | 宣言といっしょに選ぶものの組み合わせ（同じ力の 2 回の指定・`with_power` と `with_powers` の併記・クチバシティジムとワザの組） | 入力の検査（`check`・`submit` で完成した `UseAttack` に `check_use_attack`）。ゲーム上できない組み合わせは `CANDIDATE_INPUT_INVALID`、止める組み合わせは `CANDIDATE_NOT_EXECUTABLE` |
| C. コイン・検索の開始のあとで決まる | コインの結果・こんらんの「うら」・山札の中身・検索の選択肢・きぜつ・サイド | 受理のあと（エンジンの処理と既存の決定）。候補は評価しない |
| D. 今の実装では候補の段で安全に判断できない | 宣言の前の先読みが試すコインの結果・ワザの途中の決定の答えで当たる停止（HC1 など）・自分のうらのバトル場のポケモンのワザ | 候補では呼ばない（`preflight_not_evaluated`・`face_down_reveal_not_evaluated`）。最終の判定は `apply_command` |

`checks.attack_request` が読むもの（v0.147〜v0.151 の調査と同じく、使う前の確かめの読む値をたどった）: 自分のバトル場のポケモンの状態・特殊状態・持続する効果・マーカー・ついている
エネルギー（`attack_cost_payable`・`attack_cost_problem`）、場の公開のポケモンの特殊能力（`scared_by`・許可・［サイコリンク］）、相手のバトル場のポケモンの今の姿（［へんしん］・
［ものまね］。うらなら読まない）、ログの公開の記録（前の番のワザ）、ベンチの数。19 の `usage_problem` の実装は、ベンチの数・ダメージ・マーカー・ついているエネルギーカード・
相手の控えの有無だけを読みます。宣言といっしょに選ぶものの確かめ（`stadium_attack_coin_available`・`attack_power_check`・`group_attack_powers_check`）も、場のスタジアム・
場のポケモンの特殊能力・特殊状態・ついているエネルギー・その番の使用の記録だけを読みます。山札・サイド・相手の手札の中身は読みません（双子のテストで確かめた）。

宣言の前の先読み（`preflight.after_real_run`・`derived`）は、実際の処理のあと、まだ試していないコインの結果とワザの途中の決定の答えを状態の複製の上で試し、どれかの枝で停止に
当たれば宣言を拒否します。v0.147〜v0.151 で、この先読みが山札・サイドの配分で受理・拒否・理由の文を変えないように直していますが、先読みは実際の状態の複製（秘密の配分を含む）と
乱数の位置の上で動くので、**候補の作成・`inputs`・`check` には持ち込みません**。そのため、ワザの候補は `supported` にせず、`may_stop_later`（理由 `preflight_not_evaluated`・
`continuation_not_evaluated`）で示します。

## 4. 候補と入力の形

- 種類 `use_attack`（`MAIN_KINDS` の並びで、番の基本の操作のあと）。ゲーム上宣言できるワザがなければ候補を作らない（`scope_kinds` には入る。`offered_kinds` には入らない）
- 1 段目 `role: attack`（`meaning: attack`・1 個）: 選べるワザ。表示の項目は `card`・`card_id`（印刷したカード）・`attack_index`・`route`・`provider`・`payer`・`grantors`・
  `name_ja`・`cost`・`damage`（ダメージの表示）・`text_ja`・`eligible`・`processability`・`reasons`
- 2 段目 `role: declaration_options`（`meaning: declaration_option`・0 個以上・`decline: true`・`order: significant`・`order_preserved: true`・`depends_on_stage: 1`）:
  宣言といっしょに選ぶもの。`addon` は `stadium_coin`（`card`・`card_id` はスタジアム）・`attack_power`（`pokemon`）・`with_power`（場のポケモンと `power` の名前）。1 段目の番号ごとの
  選べる組は `options_by_choice`（U7-3 と同じ形）
- 入力 `choices`: `[ワザの番号, 宣言といっしょに選ぶものの番号, ...]`。並びは変えずに送る（`with_power` は選んだ順に宣言）。番号は応答ごとの不透明な値（`o1`…）で、uid・名前から
  作らない
- ゲーム上できない組・数・段の並び・重なり・知らない番号は `CANDIDATE_INPUT_INVALID`。止める選択（未裁定・未対応）は `CANDIDATE_NOT_EXECUTABLE`。どちらもエンジンに渡さない（状態は
  変わらない。取っ手は失効しない）

## 5. 処理可能性・coverage

| 場面 | 処理可能性 | 理由 |
|---|---|---|
| 確かめを通るワザ・組 | `may_stop_later` | `continuation_not_evaluated`・`preflight_not_evaluated` |
| 選ぶと止めるワザ（VA1 など）・止める組 | 停止のコードの分類（`unresolved_ruling`・`not_implemented`・`technical_limit`。分類がなければ `unverified`） | `stops_before_acceptance` |
| 自分のうらのバトル場のポケモン（マチスの秘策） | `unverified`（本人が知る本当のカードの印刷のワザ。エンジンがおもてにしてから確かめる） | `face_down_reveal_not_evaluated` |
| うらのカードに印刷のワザがない | `not_implemented`（入力の形を作らない） | `face_down_reveal_not_evaluated`・`no_printed_attack` |
| 状態の規約集合を扱えない | `not_implemented` | `state_not_supported` |

- `supported` は使わない（`guarantees.supported_scope`）。`unverified` は秘密の情報を示してよいという意味ではない（`input_disclosure` は別の軸。ワザの入力は `confirmed`）
- `coverage.scope_kinds` は `MAIN_KINDS` の 13 種類、`not_covered_kinds` は `play_trainer`・`use_power`・`use_stadium`・`remove_disguise`・`discard_from_play`・`reveal_face_down`・
  `check_face_up_deck`。`completeness` は `partial`
- うらのバトル場のポケモンのワザといっしょに選ぶものは示さない（おもてにする前に確かめられない。U7-4 の未対応）

## 6. 既存エンジンとの一致・意図した API の差

- `check_use_attack` への関数化で、宣言の確かめの順番・停止のコード・理由の文・副作用は変えていない（`_use_attack` は同じ関数を呼ぶ）
- U7 経由・`client_api` 経由・直接の `UseAttack` で、受理のあとの状態・乱数・ログ・診断が同じ（構築盤面の各場面と、`new_game` からの接続の列）
- 意図した差:
  - 選ぶと止めるワザ・組を選ぶと、ホストの段で `CANDIDATE_NOT_EXECUTABLE`（エンジンに渡さない）。直接送れば、エンジンの拒否（`rejected`・停止の診断）
  - ゲーム上できない組み合わせは `CANDIDATE_INPUT_INVALID`（直接送れば、エンジンの拒否）
  - 宣言の前の先読みで止まるワザ（こんらんのほのおのうずの HC1 など）は、候補では `may_stop_later` のまま。送るとエンジンの拒否（`rejected`・`unresolved_ruling` の診断。状態は
    変わらず、取っ手は失効しない。相手・観戦者への更新は作らない）。拒否と、受理のあとの決定の答えで止まる（ドライアップの DU1。`accepted`・`halted`）は結果で区別できる
  - 番の候補にワザの候補が加わった（U7-1・U7-3 のテストの、候補の種類と `not_covered_kinds` の期待を直した）

## 7. client_api（GUI への契約）

要求の形は同じ（`candidates`・`inputs`・`check`・`submit`）。契約・形式の版は変えていません（`kyuura-client-api`・形式 1、`kyuura_legal_actions_format` 1）。応答の形は加える方向だけ
（新しい種類 `use_attack`・段の `role: attack`・`declaration_options`・選べるものの `attack_index`・`route`・`cost`・`damage`・`addon` など）です。**同じ形式の版でも、既存の GUI が
ワザの候補を扱えるとは限りません**（知らない `kind`・`role` を表示・入力できるかは GUI の実装による）。

### 7.1 JSON の例

ワザの候補（`candidates` の応答の 1 件）:

```json
{"id": "c2", "kind": "use_attack", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"],
 "guarantees": {"preconditions": "…check_use_attack…", "acceptance": "保証しない。…宣言の前に先読み…", "after_acceptance": "評価していない…", "supported_scope": "ワザの候補は supported にしない…"},
 "choices_format": "[ワザの番号, 宣言といっしょに選ぶものの番号, ...]（いっしょに選ぶものは選んだ順。0 個でもよい）",
 "input_disclosure": "confirmed", "input_stages": [{"stage": 1, "input": "choose_option"}, {"stage": 2, "input": "choose_option"}]}
```

1 段目の選べるワザ（`inputs` の `stages[0].options` の 1 件）:

```json
{"id": "o2", "card": 0, "card_id": "PMCG1-014", "attack_index": 1, "route": "form", "name_ja": "ひのこ", "cost": ["fire", "colorless"], "damage": "30",
 "text_ja": "自分の「炎」エネルギーカードを1枚はがしてすてる。", "eligible": true, "processability": "may_stop_later",
 "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]}
```

2 段目（クチバシティジムのコインを選べる盤面）:

```json
{"stage": 2, "input": "choose_option", "role": "declaration_options", "meaning": "declaration_option", "count": {"min": 0, "max": 1},
 "options": [{"id": "o3", "addon": "stadium_coin", "card": 4, "card_id": "PMCG5-076", "eligible": true, "processability": "may_stop_later", "reasons": ["…"]}],
 "depends_on_stage": 1, "options_by_choice": {"o1": [{"option": "o3", "eligible": true, "processability": "may_stop_later"}], "o2": [{"option": "o3", "eligible": true, "processability": "may_stop_later"}]},
 "distinct": true, "decline": true, "order": "significant", "order_preserved": true}
```

宣言の送信と、宣言のあとの決定への接続:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c2", "choices": ["o2"]}
→ {"ok": true, "outcome": "accepted", "result": {"status": "awaiting_decision", "next": [{"kind": "answer_decision", "player": 0}], …}, "refetch_required": true}
{"contract": "kyuura-client-api", "format": 1, "type": "candidates"}
→ candidates: [{"id": "c1", "kind": "answer_decision", …}]
{"type": "inputs", "candidate": "c1", …}
→ stages: [{"decision_kind": "discard_energy", "meaning": "card", "count": {"min": 1, "max": 1}, "options": [{"id": "o1", "card": 1, "card_id": "PMCG1-098", …}, {"id": "o2", …}]}]
{"type": "submit", "candidate": "c1", "choices": ["o1"], …}
```

コイン・停止・拒否の表示の例:

| 応答 | 表示の例 |
|---|---|
| 候補・選べるものの `processability: may_stop_later`（`preflight_not_evaluated`） | 「宣言できます。エンジンが宣言を確かめるときに、扱えない場合として断ることがあります」 |
| 選べるものの `eligible: false`・`processability: unresolved_ruling`（`stops_before_acceptance`） | 「このワザは、今の規約集合では扱えません（ゲーム上の禁止ではありません）」。送ると `refused`・`CANDIDATE_NOT_EXECUTABLE` |
| `submit` が `refused`・`CANDIDATE_INPUT_INVALID` | 「この組み合わせでは宣言できません」（エンジンに渡していない。取り直さなくてよい） |
| `submit` が `rejected`・`category: unresolved_ruling`（HC1 など） | 「この場面の扱いは決まらないため、エンジンが宣言を受け付けませんでした」（状態は変わらない。番は続く） |
| `submit` が `accepted`・`status: awaiting_decision` | 決定の入力へ（`candidates` を取り直す） |
| `accepted` のあとの `status: halted` | 「処理できない場面で対戦が止まりました」（`halt` を表示する） |
| コイン | 入力にしない。結果は更新の観測（`coin_flip` のログ）で表示する |

## 8. GUI 側の追従（GUI リポジトリは変更していない）

- 固定するコミット: `9506d6305e90ec262fbe77740d9aa57f04b980b6`（ブランチ `claude/u7-4-attacks`。版 0.166.0。依存は `kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@9506d6305e90ec262fbe77740d9aa57f04b980b6`）。このコミットをクリーンな仮想環境へ Git の URL から通常のインストールで入れ、`scripts/smoke_installed_package.py` で `client_api` 経由のワザの宣言の受理を確かめた（編集可能インストール・PYTHONPATH は使っていない）。このあとのコミットは、この記録だけの文書の変更
- 契約: `kyuura-client-api`・形式 1、`kyuura_legal_actions_format` 1（変えていない。応答の形を加えただけ。既存の GUI がワザの候補を扱えるとは保証しない）
- 型: 候補の `kind: use_attack`、段の `role: attack`・`declaration_options`、`meaning: attack`・`declaration_option`、選べるものの `attack_index`・`route`・`provider`・`payer`・
  `grantors`・`name_ja`・`cost`・`damage`・`text_ja`・`addon`・`power`・`face_down`、`options_by_choice`（U7-3 と同じ形）
- 検証: 1 段目は 1 個、2 段目は `options_by_choice[1 段目の番号]` の中から 0 個以上・重なりなし。並びは送るまで変えない。送る前に `check` を呼ぶ
- 入力画面: ワザの一覧（名前・必要なエネルギー・ダメージの表示・説明・出どころ）→ 宣言といっしょに選ぶもの（なければ省く）→ 送信。対象・トラッシュ・検索・写すワザは、受理のあとの
  `answer_decision` の候補で選ぶ（宣言の画面に入れない）
- 表示: `processability` ごとに区別し、`unresolved_ruling`・`not_implemented` を「ゲーム上できない」と表示しない。`refused` と `rejected` と `accepted`（そのあとの `halted`）を分ける

## 9. 制限・引き継ぎ

- ワザの候補は `supported` にしない（宣言の前の先読み・受理のあとを評価しない）。本人の知識だけで先読みの停止を判定する共通関数は、まだない
- 自分のうらのバトル場のポケモンのワザは `unverified`（エンジンの確かめは呼ばない）。うらのカードで宣言といっしょに選ぶものは示さない。印刷のワザがないうらのカードは `not_implemented`
- U7-5: トレーナー・特殊能力・スタジアム・`RemoveDisguise`・`DiscardFromPlay`・`RevealFaceDown`・`CheckFaceUpDeckCard`。宣言といっしょに選ぶものの表し方（`options_by_choice`・
  入力の検査でのエンジンの確かめ）と、処理の前半を関数にして候補の作成に使う方法は、そのまま使える
