# 設計の変更（v0.12）

v0.12 は R団のファイヤー（PMCG5-020）の「ふしちょう」（きぜつしたあとに使う特殊能力）と「ほのおのかべ」（番をまたいではたらくワザの効果）を加えました。目標は次の 2 つです。

- 目標A: きぜつしたポケモンを、正しいタイミングでトラッシュから手札にもどせること（[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md)・[phoenix-v0.12.md](phoenix-v0.12.md)）
- 目標B: 期限付きのワザの効果を、正確に保持・適用・失効させられること（[temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md)・[rocket-moltres-v0.12.md](rocket-moltres-v0.12.md)）

汎用のイベントの仕組みは作っていません。v0.2a の決定、v0.2f のきぜつの処理、v0.4b の持続する効果、v0.10 のダメージの処理の境界（`deal_attack_damage`・`finish_damage_elements`）をそのまま使い、境界を 2 か所（きぜつの処理の前の候補・勝ち負けの判定とバトル場に出すあいだの決定）と、持続する効果の種類を 1 つ加えました。

## 1. v0.11 の処理の順番（前提）

```
_use_attack
  ├ 宣言の前の確認（effect.problem・こんらんのダメージの変更効果・C18・G37）
  ├ 宣言（attack）→ こんらんのコイン
  ├ effect.resolve（ダメージの要素 → finish_damage_elements（はんげき）→ ダメージ以外の効果）
  └ _finish_attack
       ├ _ko_prevention_offer（こんじょう。番でないプレイヤーのポケモンだけ）→ 決定 KO_PREVENTION
       └ _knock_out_after_attack: HP 以上をきぜつ（_knock_out）→ _after_knockouts（サイド → 勝ち負け → バトル場に出す → 番の終わり）
_end_turn → remove_expired_persistent_effects → _pokemon_check（どく → きぜつ → _after_knockouts(then=next_turn) → ねむり・マヒ → 次の番）
```

v0.12 で変えたところ:

- 宣言の前の確認に W24（`retaliation_double_knockout_problem`）を加えた（G37 のあと、こんらんのコインの前）。
- `deal_attack_damage` が、相手の「ほのおのかべ」の記録（`AttackUse.retaliations`）をつけ、`finish_damage_elements` が与える。
- `_ko_prevention_offer` が番のプレイヤーのポケモンも見る（「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモン。W26）。
- `_knock_out_after_attack`・`_pokemon_check` が、きぜつの処理の前に「ふしちょう」の候補を求め、`_after_knockouts` に渡す。
- `_next_prize_or_judge` が、勝ち負けの判定で対戦が続くなら、バトル場に出す前に「ふしちょう」の決定を出す（`_offer_post_knockout`）。バトル場に出す処理は `_promotions_after_judge` に分けた（中身は v0.11 と同じ）。

## 2. きぜつしたあとの能力の設計案の比較（B1）

| 観点 | 案A きぜつの処理の中で直接解決 | 案B きぜつの処理を分け、きぜつしたあとの境界をつくる | 案C きぜつしたカードを発動の候補として持つ | 案D 汎用のイベントの仕組み |
|---|---|---|---|---|
| 原典との整合 | 「使える」（任意）を表せない（決定を出せない） | p.311（任意）・p.82（トラッシュのあと）を表せる | 同じ | 同じ |
| 使用の任意性 | × | 決定（v0.2a） | 決定 | 購読者ごとの決定 |
| トラッシュへの移動 | きぜつの処理のまま | きぜつの処理のまま | きぜつの処理のまま | 書き直しが要る |
| uid の保持 | ○ | ○ | ○（候補に uid を持つ） | ○ |
| サイド・補充・勝ち負け | 処理の途中で止められない | 境界の位置で順番を決める | 候補を運べば、既存の順番のまま差し込める | 境界ごとに発行が要る |
| 保存・復元 | — | 決定の `context` | 決定の `context` | 購読の状態を保存する仕組みが要る |
| ログの監査 | — | 既存の組み立て直しに足す | 同じ | 新しい規約が要る |
| API 互換 | ○ | ○（決定の種類を 1 つ足す） | ○ | 大きく変わる |
| 複雑さ | 小（ただし任意性が表せない） | 中 | 小〜中 | 大 |

採用は **案B と案C の組み合わせ**: きぜつの処理の前に候補（案C。(持ち主, uid, カード id, パワーの位置)）を求め、サイドを取る決定の `context` で運び、勝ち負けの判定とバトル場に出すあいだの 1 か所（案B の境界）で決定を出す。案D（汎用のイベントの仕組み）は、対応カードにきぜつしたときの能力が 1 つしかなく、ほかの境界（ダメージ・きぜつするとき）は v0.10・v0.11 の仕組みで足りるので採らなかった。

## 3. カードの識別と任意性（B2・B3）

- 識別の情報は (持ち主, uid, カード id, パワーの位置) だけ（[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 4 章）。特殊状態・かがくへんかガスは、トラッシュの前に「使えるか」を判定し、使えない場合は候補にしない。場をはなれたあとの状態で過去の特殊状態・抑止を判断しない。
- 任意（P2。SUPPORTED）なので、決定で選ばせる。決定の種類は新しく `POST_KNOCKOUT_POWER`（再開先 `post_knockout`）にした。v0.11 の `KO_PREVENTION`（再開先 `knock_out`）と同じ種類にしない理由は、選べるもの（トラッシュのカードの uid と場のポケモンの番号）・続き（バトル場に出すか、きぜつの処理に入るか）・不変条件（場に HP 以上のポケモンが残ることを許すか）がちがうこと（[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 1 章）。名前は既存の決定の種類（`ko_prevention`・`recover_energy`）にならい、カードの名前でなく、はたらく時点で付けた（候補の `phoenix_recovery` は採らなかった）。

## 4. トラッシュから手札・サイドと勝ち負け（B4・B5）

- トラッシュのカードを手札に加えるのは `zones.return_discard_to_hand` だけ（B4 の 10 項目と確かめる場所は [post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 6 章）。v0.9 のゴースの「エナジーへんかん」の手札に加える処理もこれに置きかえた（動きは同じ。tests/test_haunter_line_v0_9.py と、ゴーストの組の自然な対戦の固定値（tests/test_haunter_games_v0_9.py の指紋）・ストレス実行の数が v0.11 と同じ）。
- 手札にもどすことは、きぜつの取り消しではない（p.82 の解説）。きぜつの成立（HP 以上）→ 場からはなれる・トラッシュ（`_knock_out`。持続する効果もここで消える）→ サイド（取る数はきぜつの数）→ 勝ち負けの判定（p.311 の表）→（対戦が続くなら）ふしちょうの宣言 → 手札に加える → バトル場に出す、の順に分けた。
- 順番は原典で決まらない（P27・P28・P30）ので正規化した。どの順番でも、だれがどのカードを選べるか・勝ち負けとその理由が変わらないことは [post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 3 章。勝ち負けが決まるより「ふしちょう」が必ず先だとは決めていない（対戦が終わるなら決めさせない）。決定を待つ間に勝ち負けは確定しない（勝ち負けの判定は決定の前に終わっていて、続く場合だけ決定を出す）。

## 5. 保存形式（B7）

形式 9 のまま（[temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) 5 章）。

| 状態 | 形式 9 での表し方 | 形式 1〜8 |
|---|---|---|
| 「ほのおのかべ」の効果（`Retaliation`） | `persistent_effects` の 1 つ（`"effect": "retaliation"` と `"attack_index"`・`"amount"`） | 形式 8 は同じ。形式 1〜7 は `ValueError`（v0.4b と同じ） |
| 「ふしちょう」の決定 | `decision`（`kind` `post_knockout_power`・`resume` `post_knockout`・`context` の `power`・`then`） | 形式 2〜8 は同じ。形式 1 は `ValueError` |
| サイドを取る決定の「ふしちょう」の候補 | `decision.context` の `post_knockout` | 形式 2〜8 は同じ。形式 1 は `ValueError` |

なぜ形式 10 が要らないか: 新しい状態の項目（`GameState`・`PokemonInPlay` の属性）を加えていない。持続する効果の種類の値と、決定の種類・再開先・`context` の値を加えただけで、形式 8・形式 2 からある項目で表せる。既存の値の意味は変えていない（`prevent_damage` の形・`take_prize` の決定の形は、候補がなければ v0.11 と同じ）。v0.3b〜v0.3c で特殊状態の値を、v0.4d〜v0.11 で決定の種類を加えたときも形式を変えていない。

互換性: 効果・決定のない状態は、形式 1〜9 で v0.11 と同じ書き出し（v0.1 の参照データ・比較の駆動の参照データ compat_base_4bd97bf.json はそのまま通る）。v0.11 の状態を読む側は、知らない種類の効果・決定を拒否すること。エンジンに書き出しから状態を戻す関数はない（v0.11 と同じ）。保存・復元は pickle・deepcopy・clone で確かめた（[v0.12-verification.md](v0.12-verification.md)）。

## 6. 期限付きの効果と「はんげき」との比較（B6・B8）

- 持ち方は案B（状態の `PokemonInPlay.persistent_effects`）。案A（ワザ 1 回の中）は番をまたげない、案C（ログから求め直す）はログを正本にしてしまう（[temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) 1 章）。
- 「はんげき」との比較表は [temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) 4 章。共通にしたのは、原典で同じとわかる部分（与える時点・与える相手・すでに HP 以上なら与えない・宣言の前の止め方）だけ。ダメージの計算（ワザによるダメージ）は `deal_attack_damage` を通し、`_apply_counterattack` を流用していない。

## 7. 未解決の裁定の停止（B9）

新しく原典で決められないとしたもの:

| ID | 事項 | 扱い |
|---|---|---|
| W24 | R団のファイヤーがワザのダメージで、ワザを使ったポケモンが「ほのおのかべ」のダメージで、そろってきぜつする | ワザの宣言の前（G37 のあと、こんらんのコインの前）に `UnsupportedError`（`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`）。既存の止める処理（C18 と同じ形）。同じコインの結果でいっしょに起こるダメージの組（`pairs()`）だけを評価する |
| P19 | かがくへんかガスを持つポケモンと R団のファイヤーが同時にきぜつする | 未到達（W24・`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT` が先に止める）。起こったら `RuntimeError` |
| P32 | きぜつしたときに使える特殊能力の候補が 2 つ以上 | 未到達（同上）。起こったら `RuntimeError` |
| P27・P28・P30 | 「ふしちょう」とサイド・バトル場に出す・勝ち負けの順番 | 止めない。結果が変わらないので正規化（[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 3 章） |

既存の未解決の裁定に新しいカードで届くか:

| 既存 | 新しいカードで | 扱い |
|---|---|---|
| C18（はんげきで両方がきぜつ） | R団のファイヤーがカイリキーにワザを使う場合は既存のまま。「ほのおのかべ」のダメージで、ワザを使ったカイリキーの「はんげき」が R団のファイヤーに与える 10 は、W24 の判定に数える | 変えていない（v0.10 の止める処理のまま） |
| C34・C35（1 つのワザで 2 つ以上の「はんげき」） | 「ほのおのかべ」と「はんげき」が 1 つのワザで合わせて 2 つ以上はたらくことは起こらない（「ほのおのかべ」の効果を持つのは「はんげき」のない R団のファイヤーだけ。自分へのダメージは相手のワザではない）。「ほのおのかべ」のダメージで「はんげき」がはたらくのは別のダメージの要素（`retaliation_use`）の中 | `RuntimeError` の対象を「はんげき」と「ほのおのかべ」の合計にした（今の対応カードでは起こらない） |
| G37（こんじょうとワザの効果） | 「ほのおのかべ」は相手に効果を与えない（`opponent_effect_elements` は空）。「ほのおのかべ」のダメージで HP 以上になったワザを使ったポケモンの「こんじょう」のあとに、そのワザの相手への効果（ふきとばし）が残る場合でも、効果を受けるのは相手（R団のファイヤー側）で、「こんじょう」のポケモンではない | 変えていない |
| G40（こんじょうの候補が 2 匹以上） | 番のプレイヤーのポケモンも候補になった（W26）が、R団のファイヤーとワザを使ったポケモンがそろって HP 以上になる場合は W24 が先に止めるので、2 匹にならない | `RuntimeError` のまま |
| T27（複数の「とうめい」のコインの順番） | 「ほのおのかべ」のダメージを受けるゴーストの「とうめい」は、別のダメージの要素（`retaliation_use`）の中で 1 回。きっかけのワザの相手は R団のファイヤー（「とうめい」なし） | 起こらない（変えていない） |
| R13（あまごいのあとの通常の操作） | 関係しない | 変えていない |

既存の未解決の裁定 19 件（コードのある 16 件）は、コード・止める条件・テストを変えていない。v0.12 で 3 件（W24・P19・P32）を加えて 22 件（コードのある 17 件）。P27・P28・P30 は、結果が変わらないので止めずに正規化した（v0.2f のサイドを取る順番と同じ扱いで、件数に数えていない）。

## 8. ログ

| イベント | 加えた版 | 意味 |
|---|---|---|
| `post_knockout_power_declined`・`post_knockout_power_declared` | v0.12 | 「ふしちょう」を使うかの答え |
| `return_to_hand` | v0.12 | トラッシュから手札に加えた（`revealed`） |
| `retaliation`・`retaliation_skipped` | v0.12 | 「ほのおのかべ」のダメージを与える・与えない |
| `damage`（`retaliation` True） | v0.12（項目を加えた） | 「ほのおのかべ」のダメージ（`effect`・`pokemon_id` も加えた） |
| `persistent_effect_skipped` | v0.12 | 相手の「はんげき」で HP 以上になったので「ほのおのかべ」の効果を与えない |

既存のイベント（`knock_out`・`take_prize`・`persistent_effect_added`・`persistent_effect_removed`・`ko_prevention_*`）の形は変えていない。

## 9. 原子性（C4）

- 不正な答え・ほかの操作は、決定の確認（v0.2a）・段階の確認で `IllegalActionError`（`apply_command` は clone してから処理するので、状態・ログ・乱数は変わらない）。
- W24 は宣言の前（乱数を使う前）に止める。`retaliation_double_knockout_problem` は状態を変えない計算（`preview_attack_damage`）だけを使う。
- 「ふしちょう」の決定を出す・答えるで乱数を使わない。
- 決定を待つ間の状態は、pickle・deepcopy・clone で保存して続けられる。

## 10. エラーコード

| コード | 種類 | いつ |
|---|---|---|
| `UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT` | `UnsupportedError` | W24。ワザの宣言の前 |
| `POWER_NOT_USABLE_NOW` | `IllegalActionError`（v0.11 からある） | 場にいる R団のファイヤーで `UsePokemonPower`（「ふしちょう」はきぜつしたときだけ） |

エンジンが止める `UNRESOLVED_…` は 17 件（v0.11 の 16 件は変えていない）。

## 11. 不変条件

- 「ふしちょう」の決定（`_post_knockout_decision_problems`）・サイドを取る決定の候補（`_post_knockout_candidate_problems`）（[post-knockout-powers-v0.12.md](post-knockout-powers-v0.12.md) 7 章）。
- 「ほのおのかべ」の効果（`_persistent_effect_problems` の `Retaliation`・`_retaliation_problems`）（[temporary-attack-effects-v0.12.md](temporary-attack-effects-v0.12.md) 6 章）。
- v0.10 の例外（`_counter_knocked_out_attacker_awaiting`。ふきとばしの決定を待つ間、HP 以上のワザを使ったポケモンが残る）は、「ほのおのかべ」のダメージ（`damage` の `retaliation`）でも当てはまるようにした。
- v0.11 の「こんじょう」の決定（`_ko_prevention_decision_problems`）は、番のプレイヤーが決定する場合（選べるものがワザを使ったポケモンで、「ほのおのかべ」のダメージを受けた）を許すようにした。

## 12. ログの監査（tests/log_audit.py）

v0.12 で加えた確認:

- 「ふしちょう」: きぜつのたびに、そのときのいちばん上のカード・組み立て直した特殊状態・はたらいているかがくへんかガスから「使えるか」を求め、答えの有無・重複・時点（サイドのあと、バトル場に出す前）・宣言のすぐあとの `return_to_hand`・使えないのに答えた、を確かめる。`return_to_hand` を手札とトラッシュの組み立て直しに含める。
- 「ほのおのかべ」: `persistent_effect_added`・`persistent_effect_removed` から、はたらいている効果を組み立て直し、相手のワザのダメージを効果のあるポケモンが受けたら、そのワザの中に `retaliation`（またはすでに HP 以上なら `retaliation_skipped`）が 1 回あること・ダメージ以外の効果・きぜつより先にあること・量（基本となるダメージ = `amount`）・弱点・抵抗力の印・与える相手（ワザを使ったポケモン）を確かめる。期限で消えるのが早すぎる・遅すぎる・`turn_end` のあとに残る、も見つける。
- 「とうめい」・「はんげき」の確認は、「ほのおのかべ」のダメージ（別の窓 `ret`）でも同じく行う。番のプレイヤーの「こんじょう」の答えを許す。

ログだけで確かめられないこと: 決定の中身（選べるもの・`context`）はログにないので、答えとの対応はエンジンの不変条件で確かめる（v0.11 と同じ）。

## 13. 変えたもの

| ファイル | 変更 |
|---|---|
| kyuura_engine/state.py | `Retaliation`。`PERSISTENT_EFFECT_TYPES` |
| kyuura_engine/persistent.py | `retaliation`（今の番にはたらく効果） |
| kyuura_engine/zones.py | `return_discard_to_hand` |
| kyuura_engine/decisions.py | `POST_KNOCKOUT_POWER`。`push_attack_decision` の確認に `retaliations` |
| kyuura_engine/effects.py | `AttackUse.retaliations`・`deal_attack_damage` の記録（`log_extra`）・`finish_damage_elements`・`PendingRetaliation`・`retaliation_use`・`_apply_retaliation`・`retaliation_double_knockout_problem`・`DamageAndRetaliation`・`ReturnToHandOnKnockOut`・`post_knockout_power`・登録（id `kyuura-engine-0.12`）。`RecoverEnergyAndSelfDamage` は `return_discard_to_hand` を使う |
| kyuura_engine/engine.py | W24 の確認、こんじょうの候補に番のプレイヤー、`_post_knockout_candidates`・`_offer_post_knockout`・`_resume_post_knockout`・`_promotions_after_judge`、不変条件 |
| kyuura_engine/serialize.py | `retaliation` の項目。形式 1 の `ValueError` |
| kyuura_engine/cards.py・scripts/extract_kyuura_cards.py・data | `pool_v0_12`（PMCG5-020）。写しを作り直した |
| kyuura_engine/data/card_verification.json | PMCG5-020 |
| kyuura_engine/__init__.py・pyproject.toml | 版 0.12.0。`Retaliation` を公開 |
| tests/log_audit.py | 12 章 |
| tests/helpers.py | `ROCKETS_MOLTRES`。`build_test_state` の `"retaliation"` |
| tools/stress_engine.py | 組 `moltres`・`moltres_mixed`。`POWER_USERS` の最後に R団のファイヤー（ほかの組の乱数の使い方は v0.11 と同じ） |

## 14. 変えなかったもの

- 比較の駆動（tools/compat_driver.py）と参照データ（tests/fixtures/compat_base_4bd97bf.json・tests/fixtures/v0_1_reference.json）。
- 既存の未解決の裁定のコード・止める条件（7 章）。
- v0.11 の「こんじょう」の処理の順番（番のプレイヤーのポケモンを候補に加えただけ）。
- 書き出しの形式（9 のまま）。
- 参照する kyuura のコミット（`ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`）。kyuura は変更していない。

## 15. 変えた既存のテストと理由

| テスト | 理由 |
|---|---|
| 自然な対戦の固定値のテスト（v0.4a〜v0.11 の `…_games_…`）・tests/test_rng_and_serialize.py・tests/test_trainers.py | 登録表の id が `kyuura-engine-0.12` になった（固定値の指紋は変わらない） |
| tests/test_cards.py・tests/test_effects.py・tests/test_pokemon_powers_v0_5.py | 対応カード・ワザ・パワーの一覧に R団のファイヤーを加えた |
| tests/test_effect_preflight_v0_3d.py | `ATTACKS` に「ほのおのかべ」を加えた（CLAUDE.md の約束） |
| tests/test_unresolved_boundaries_v0_4e.py | `ALL_CODES` に W24 を加え、`RetaliationDoubleKnockoutBoundaryTest` を加えた |

## 16. 次の版への提案（実装していない）

- 「きぜつしたとき」のほかの特殊能力（［ふしちょう］と同じ形）・きぜつを防ぐトレーナー（きあいのハチマキ。ネオ。範囲外）を加えるときは、P32・G40 の順番を原典で確かめ、止める処理を加える。
- 「相手の番ではたらく効果」のほかのワザ（わるいカメールの「こうらがえし」。p.89。返すダメージが受けたダメージと同じ）を加えるなら、`Retaliation` の量を「受けた最終ダメージ」にする形を検討する（「（ダメージ以外の効果は与えない）」の扱いも照合する）。
- 相手に与える持続する効果（すなかけ・からまるいと）は、発生源が自分自身という不変条件を見直す。
