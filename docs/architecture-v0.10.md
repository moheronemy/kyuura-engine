# 設計の変更（v0.10）

v0.10 は、カイリキー（PMCG1-057。ポケモンカード第1弾）のポケモンパワー「はんげき」（相手のワザによってダメージを受けたとき、きぜつしても、ダメージを与えたポケモンに弱点・抵抗力に関係なく 10 ダメージ。ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない）と、ワザ「ちきゅうなげ」、進化元のゴーリキー（PMCG1-055。からてチョップ・じごくぐるま）を加えた版です。ワンリキー（PMCG1-053。けたぐり）は v0.1 から対応しています。

関連する文書:

- 原典の照合と裁定: [counterattack-v0.10.md](counterattack-v0.10.md)（C1〜C43・A4）と [machamp-line-v0.10.md](machamp-line-v0.10.md)（M1〜M12）
- ダメージを受けたあとに自動的にはたらく特殊能力の仕組み: [post-damage-powers-v0.10.md](post-damage-powers-v0.10.md)
- 確かめた結果: [v0.10-verification.md](v0.10-verification.md)

新しく加えたのは次のものだけです。

- 自動的にはたらく特殊能力の実装 `CounterattackDamage`（`declared = False`）
- ワザ 1 回の中だけの記録 `AttackUse.counterattacks` と、ダメージの処理の終わりの境界 `finish_damage_elements`
- 公開の問い合わせ `working_counterattack_power`
- 2 つのワザの実装（`DamageReducedByOwnCounters`・`DamageAndSelfDamage`）と、ワザのダメージの候補の宣言 `AttackEffect.damage_profile`
- 3 つのログのイベント（`counterattack`・`counterattack_skipped`・`drain_heal_skipped`）
- 1 つの `UNRESOLVED_…` のコード
- 不変条件の 1 つの例外（ワザの途中の決定を待つ間の、「はんげき」で HP 以上になったワザを使ったポケモン）

状態の項目・書き出しの形式（9 のまま）・コマンドの種類・段階・決定の種類は加えていません。

## 1. 既存の構造（B1）

v0.9 で、ワザによってダメージや効果を受ける直前に自動的にはたらく特殊能力（「とうめい」）を、ワザの要素の処理の境界（`effects.attack_reaches`。ダメージは `deal_attack_damage` の中）で評価する仕組みを加えました。v0.10 で再利用したもの・しなかったもの:

| 部品 | 再利用 | 理由 |
|---|---|---|
| `deal_attack_damage`（どのワザのダメージもここを通る。v0.2f） | **する**（判定する場所） | 相手のワザのダメージを受けたことが分かるのはここだけ。最終ダメージ（p.321）・「ダメージを受けない」状態・「とうめい」の結果もここで決まる |
| `AttackUse`（ワザを使ったプレイヤー・ポケモン・ワザ。v0.4d） | **する**（発生源と与える相手） | 「相手のワザ」「ダメージを与えたポケモン」を、重複した状態なしに表せる |
| `AttackUse.reception` のような、ワザ 1 回の中だけの記録（v0.9） | **同じ形を使う**（`counterattacks`） | 判定と与える時点のあいだだけ要る値。状態に持たない |
| `attack_reaches`（受ける前の評価） | しない | 評価の時点が違う（受けるとき・受けたとき）。`attack_reaches` の戻り値はワザの実装の処理を変えるが、「はんげき」は変えない（[post-damage-powers-v0.10.md](post-damage-powers-v0.10.md) 1 章） |
| `continuous.suppressors_of`（かがくへんかガス。v0.8） | **する** | 抑止の判定を複製しない |
| `engine._finish_attack`（きぜつ・サイド・交代・勝ち負け。v0.2f） | **変えない** | 「はんげき」は、きぜつの処理の前（ワザの処理の中）で完結する（5 章） |
| `PowerEffect.declared`（v0.8） | **する**（False） | 宣言しない特殊能力は `POWER_NOT_DECLARABLE` |

## 2. 設計案の比較（B2）

ワザの実装 20 種類（56 件）のすべてを読んで、ダメージと効果をどこで与えているかを確かめてから選びました（[post-damage-powers-v0.10.md](post-damage-powers-v0.10.md) 2.2 の表）。

| 案 | 形 | 長所 | 短所 | 採否 |
|---|---|---|---|---|
| A. 各ワザの実装から個別に呼ぶ | 実装ごとに、相手へのダメージのあとで「はんげき」を探して与える | 実装ごとの順番が見える | ダメージは 1 か所（`deal_attack_damage`）を通るのに、判定（相手のワザか・最終ダメージ・特殊状態・ガス）を実装ごとに書くと重複する。ダメージの要素だけのワザ（23 + 7 件）に書き忘れると、はたらかない（変異 1 の種類）。自分へのダメージのあとに与える（C29）ことを実装ごとに守る必要がある | 不採用 |
| B. ワザのダメージの適用の境界に、適用後の共通の評価 | 判定は `deal_attack_damage` の中（のせる直前の状態で）、与えるのはダメージの処理の終わり（`finish_damage_elements`） | 判定が 1 か所。ダメージの要素だけのワザはエンジンが与えるので、実装を変えない。効果のあるワザは 1 行（効果の前） | きぜつの処理との境界を決める必要がある（5 章）。効果のあるワザの実装に呼び出しを加える必要がある（呼び忘れは効果・決定の前の確認で止める） | **採用** |
| C. 汎用のイベントの仕組み | 「ダメージを受けた」イベントを発行し、特殊能力を購読者として登録する | 将来の特殊能力に広げやすいかもしれない | 購読者は 1 つ。イベントの順番・購読者の順番・再帰（はんげきのダメージで発行するか）・決定をまたぐ購読の状態を決める必要がある。原典で決まっていない順番（C34・C35）を仕組みが決めてしまう。連鎖を回数の上限で止める形になりやすい | 不採用（指示のとおり、今回必要のない汎用の仕組みは作らない） |

## 3. ダメージの発生源の識別（B3）

判定は、ワザのダメージの要素（`deal_attack_damage`）の中だけで行います。発生源はそこに来たことで「ワザによるダメージ」と決まり、`AttackUse.player` と受けるポケモンの持ち主を比べて「相手のワザ」かを決めます。与える相手は `AttackUse.pokemon_id` です。ほかのダメージ（自分のワザ・反動・特殊能力・ダメージカウンターの移動・どく・こんらん）がこの経路を通らない・判定しないことは、[post-damage-powers-v0.10.md](post-damage-powers-v0.10.md) 2.1 の表のとおりです。新しい状態・ダメージの種類の印は加えていません（「ダメージが増えた」ことからは判定しない）。

## 4. 処理の境界（B4）

指示の候補（1〜8）を原典と照らした結果:

| 候補 | 実装 | 原典 |
|---|---|---|
| 1. ワザの基本の確認 | `engine._use_attack`（宣言・エネルギー・ねむり・マヒ） | p.309 |
| 2. ワザの解決の開始 | 同上。原典で決められない場合（`AttackEffect.problem`・こんらんのダメージ・**C18**）はここで止める（こんらんのコインの前） | p.309 手順 5 |
| 3. 受ける前の評価（「とうめい」） | `deal_attack_damage` の中、最終ダメージのあと・のせる前（v0.9） | p.160 |
| 4. ダメージの計算 | `damage.calculate_attack_damage`（p.321 の 1〜8 段階） | p.321 |
| 5. ダメージの適用 | `receiver.damage += calc.final`（**直前に「はんげき」を判定**。受けるときの状態） | p.192「ダメージを受けるとき、すでに」 |
| 6. 適用後の評価（「はんげき」を与える） | `finish_damage_elements`。**ダメージの要素（自分へのダメージを含む）がすべて終わったところ** | p.89「相手のワザによるダメージの処理を行った後で」 |
| 7. 残りのワザの効果 | ワザの実装（ワザのコイン・特殊状態・入れ替え・回復） | p.89「ダメージ以外の効果の処理は、その後で」・p.309 |
| 8. きぜつ・サイド・勝ち負け | `engine._finish_attack`（v0.2f のまま） | p.309・p.323・p.324・p.311 |

候補の 6 は、ダメージの要素ごとではなく、ダメージの要素がすべて終わったところです（自分へのダメージのあと。C29）。きぜつの処理（8）はワザのあとなので、「はんげき」を与える前にカイリキーが場から取り除かれることはありません（C17・C30）。

## 5. きぜつの処理（B5）

| 選択肢 | 検討 | 採否 |
|---|---|---|
| きぜつの処理の前に反撃を終える | エンジンは v0.2f から、きぜつの判定・処理をワザの要素をすべて処理したあと（`_finish_attack`）にまとめている。「はんげき」はワザの処理の中（6）で与えるので、自然にきぜつの処理の前になる | **採用**（既存の時点のまま） |
| きぜつの候補を記録してから反撃する | 候補はダメージ（HP 以上か）からいつでも求められるので、記録は要らない。記録を状態に持つと書き出しの形式が要る | 不採用 |
| ワザ全体の解決のあとにきぜつの処理をまとめる | すでにそうなっている（v0.2f。p.324 の同時のきぜつ） | 既存のまま |
| 既存の決定・きぜつの仕組みを使う | サイドを取る・バトル場に出す決定（v0.2f の `TAKE_PRIZE`・`PROMOTE_ACTIVE`）と、勝ち負けの判定（p.311 の表）はそのまま使う。新しい決定は要らない | **採用** |

両方のプレイヤーのポケモンがきぜつする場合（A4-6）:

- 1 つのワザ（カイリキーへのダメージ・ワザを使ったポケモン自身へのダメージ）で 2 匹がきぜつするなら、同時のきぜつです（p.324）。v0.2f のとおり、サイドは番のプレイヤーから（正規化）、バトル場に出すのは番でないプレイヤーが先（p.323）で、勝ち負けは p.311 の表で決めます。
- カイリキーがワザで、ワザを使ったポケモンが「はんげき」できぜつするなら、同時のきぜつかが原典で決められない（C18 (b)）ので、ワザの宣言の前に止めます。止める判断は、ワザのダメージの候補（`AttackEffect.damage_profile`）と、状態を変えない計算（`preview_attack_damage`）で求めます。`damage_profile` は既定で目安の数字（`DamageOnly` など）を返し、ダメージの数がコインや状態で変わる実装（`CoinFlipDamage`・`SelfDamageOnTails`・`CoinBonusDamageAndParalyze`・`ExtraEnergyDamage`・`RecoverEnergyAndSelfDamage`・v0.10 の 2 種類）は上書きします。ダメージを変える段階（`damage_modifier`）のあるワザで上書きしていなければ `NotImplementedError` にします（黙って目安の数字を使わない）。

ワザの途中の決定（ふきとばし。相手が選ぶ）を待つ間に、「はんげき」で HP 以上になったワザを使ったポケモンが場に残る（きぜつの処理はワザのあと）ので、不変条件「場のポケモンのダメージは HP 未満」に、その場合だけの例外を加えました（`engine._counter_knocked_out_attacker_awaiting`。決定の `context` とログで確かめる。印・一覧を状態に加えない）。

## 6. 反撃のダメージ（B6）

「はんげき」の 10 は特殊能力によるダメージで、ワザによるダメージではありません（C13）。`deal_attack_damage` を通さず（`_apply_counterattack`）、次のものを計算・判定しません。

| もの | 扱い | 根拠 |
|---|---|---|
| 弱点・抵抗力 | 計算しない | p.192「「弱点・抵抗力」に関係なく」（C12） |
| ワザのダメージを変える効果（プラスパワー・ディフェンダー。p.321 の 5・7 段階） | 計算しない | p.138・p.245（C37） |
| 防ぐ効果（「ダメージを受けない」状態。v0.4b） | 起こらない（ワザを使った番に、ワザを使ったポケモンが持つことはない。持っていればエンジンの不具合として止める） | 不変条件（v0.4b） |
| 特殊能力によるダメージを減らす効果 | 対応カードにない | — |
| ダメージカウンターを直接のせる効果 | 「はんげき」はダメージ（10）。カウンターの移動（`move_damage_counter`）にしない | p.192「10ダメージ」・p.320（A4-5） |
| 「とうめい」 | 判定しない（コインを投げない） | p.159「特殊能力によるダメージや効果は受けます」（C36） |

現行のカードにない相互作用（特殊能力のダメージを減らす・ダメージを受けたときに別の特殊能力がはたらく）は一般化せず、[post-damage-powers-v0.10.md](post-damage-powers-v0.10.md) 7 章に、加えるときの確認として書きました。

## 7. 無限連鎖の防止（B7）

最新の説明で、「はんげき」は相手のワザによって受けたダメージでだけはたらき（C3）、「はんげき」のダメージはワザによるダメージではありません（C13・C14）。エンジンは判定をワザのダメージの要素（`deal_attack_damage`）でだけ行い、`_apply_counterattack` は `deal_attack_damage` を通らないので、連鎖は発生源の分類で起こりません。再帰の回数の上限は使っていません。カイリキーどうしの対戦でも 1 回だけ与える（`test_counter_damage_does_not_trigger_another_counter`・変異 21）。

## 8. かがくへんかガス（B8）

`counterattack_power` が v0.8 の `continuous.suppressors_of` を聞きます。判定の時点は「ダメージを受けるとき」（ダメージをのせる直前）で、その時点の場で求めます。ワザの宣言のときのガスの状態は使いません（ワザの処理の中でベトベトンが変わることは、今の対応カードでは起こらない）。

## 9. 乱数と原子性（B9）

- 「はんげき」に乱数は要らない（説明にコインがない。C43）。判定・与える処理は乱数を使いません。ワザのコインの回数・順番は v0.9 と同じです（「はんげき」をワザのコインの前に与えるが、乱数を使わないので、乱数の続きは変わらない）。
- 正常なワザの処理の途中で誤りが起きても、`apply_command` が複製の上で処理しているので、不完全な状態は返りません（v0.2a から。`AtomicityTest` で注入して確かめた）。拒否（`POWER_NOT_DECLARABLE`・`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`）は状態の変更の前です。

## 10. 保存形式（B10）

**形式 9 のまま（形式 10 を加えない）**。理由:

- 「はんげき」がはたらいているかは、受けるときの状態（いちばん上のカード・特殊状態・場のベトベトン）から求める。
- 「はんげき」の判定から与えるまでは、ワザ 1 回の処理の中で完結する（`AttackUse.counterattacks`）。ワザの途中の決定（ふきとばし）は与えてから出すので、決定をまたぐ発動待ちの状態はない（`push_attack_decision` が確かめる）。
- 回数・期限の情報はない。

書き出しの監査の `LATEST_FORMAT` は 9 のまま。保存（pickle・`copy.deepcopy`・`clone`・形式 9）と復元のあとも同じ結果になることは `SaveRestoreTest` と [v0.10-verification.md](v0.10-verification.md) で確かめた。

## 11. 実装（C1〜C3）

- 特殊能力: `CounterattackDamage(amount)`（`PowerEffect`）。`declared = False`、`check`（ポケモンパワー・説明文があること）、`is_working`（ねむり・マヒ・こんらんでない。どくは見ない）。`amount` は 10 の倍数の正の数。登録は `PowerKey("PMCG1-057", 0)`（印刷の文面・最新の説明・出典 P43 p.192）。
- 判定と与える処理: `effects.counterattack_power`・`working_counterattack_power`（公開）・`PendingCounterattack`・`finish_damage_elements`・`_apply_counterattack`・`counterattack_double_knockout_problem`・`_require_damage_elements_finished`・`_skip_heal_of_knocked_out_attacker`。
- ワザ: ゴーリキーのからてチョップ（`DamageReducedByOwnCounters(10)`）・じごくぐるま（`DamageAndSelfDamage(20)`）、カイリキーのちきゅうなげ（説明文なし。`DamageOnly`）。ワンリキーのけたぐりは v0.1 のまま。
- 写し: `pool_v0_10`（scripts/extract_kyuura_cards.py の `POOL_V0_10`。ゴーリキー・カイリキー）と参照カード（サカキのカイリキー PMCG6-061）。照合の記録は card_verification.json。登録表の id は `kyuura-engine-0.10`、ワザ 56 件・パワー 6 件。

## 12. ログ（C4）

| イベント | 項目 | 意味 |
|---|---|---|
| `counterattack` | `player`・`pokemon`・`pokemon_id`（「はんげき」を持つポケモン）・`power`（`PowerKey`）・`attacker`・`attacker_pokemon`・`attacker_pokemon_id`（ダメージを与えたポケモン = 与える相手）・`effect`（きっかけのワザ）・`amount`（10）・`total_damage`（与えたあとのダメージ）・`knocked_out`（与えたあと HP 以上か） | 「はんげき」を与えた。きっかけのダメージは、同じワザの中の直前の `damage`（重複させない）。カイリキーがきぜつしていても与える（そのあとのきぜつは `knock_out`） |
| `counterattack_skipped` | 上と同じ（`amount` などなし）・`reason`（`knocked_out`） | はたらいたが、与える相手がすでに HP 以上で与えなかった（C15） |
| `drain_heal_skipped` | `player`・`pokemon`・`pokemon_id`・`effect`・`dealt`・`reason`（`knocked_out`） | 「はんげき」で HP 以上になったワザを使ったポケモンの回復（メガドレイン・やどりぎのタネ）を処理しなかった（C16） |

「はんげき」がはたらかなかった理由（特殊状態・ガス・0 ダメージ）のログはありません（v0.9 の「とうめい」がはたらいていないときと同じ）。理由は、その時点の場から求められます（ログの監査が組み立て直して確かめる）。

### 12.1 ログの監査（tests/log_audit.py）

ワザごとに、ログから組み立て直したその時点の場（いちばん上のカード・ねむり・マヒ・こんらん・はたらいているかがくへんかガス）で、相手のワザのダメージ（0 より大きい）を、はたらいている「はんげき」を持つポケモンが受けたかを求め、次のことを確かめます。

- はたらいたなら、そのワザの中に `counterattack`（か `counterattack_skipped`）が 1 回あり、それより先にダメージ以外の効果（特殊状態・入れ替え・回復・ワザのコインのうち特殊状態を決めるもの）・きぜつ・番の終わりがない（p.89）。
- はたらいていないなら、`counterattack` がない（特殊状態・ガス・自分のワザ・0 ダメージ）。
- 「はんげき」のあとに、同じワザのダメージの要素がない。
- 与える相手がワザを使ったポケモン、量が登録の数、与えたあとのダメージ・きぜつの印が組み立て直したダメージと同じ。
- `counterattack_skipped` は、相手がすでに HP 以上のときだけ。
- 「はんげき」できぜつしたポケモンに回復（`drain_heal`）がなく、`drain_heal_skipped` は HP 以上のときだけ。
- 「はんげき」できぜつしたワザで、ほかのポケモンのきぜつがない（C18。エンジンが止めるはず）。
- 1 回のワザで `counterattack` + `counterattack_skipped` が 1 回まで、回復の結果が 1 回まで。
- ダメージ・サイドの組み立て直しに `counterattack` を含める。

指示の 12 種類の誤りを、自然な対戦のログを書きかえて見つけることを確かめた（tests/test_machamp_games_v0_10.py の `LogAuditCounterattackTest`。[v0.10-verification.md](v0.10-verification.md) 2.4）。

ログだけでは確かめられないこと:

- 判定の時点の特殊状態・ガスは、ログから組み立て直した値。ログにない状態の変化（盤面を直接作ったテスト）では確かめられない。
- 「はんげき」の効果の計算（弱点・抵抗力・ディフェンダーを計算しないこと）は、量が登録の数（10）と同じことで確かめる。登録の数そのものの正しさは単体テストと照合の記録で確かめる。
- サイドを取る順番（同時のきぜつで番のプレイヤーから）・バトル場に出す順番は、エンジンの不変条件（`_prize_queue_problems`。v0.4e）が確かめる。ログの監査は、サイドの数ときぜつの数の対応を確かめる。
- 原典で決められないとして止めた場合（C18 (b)）は、拒否なのでログに残らない。止めたことは、ストレス実行と単体テストで確かめる。

## 13. エラーコード

| コード | 種類 | いつ |
|---|---|---|
| `POWER_NOT_DECLARABLE` | `IllegalActionError`（v0.8 から） | 「はんげき」の使用を宣言しようとした |
| `UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` | `UnsupportedError`（新しい） | C18 (b) になりうるワザの宣言（こんらんのコインの前） |

拒否の順番の約束（v0.7 の API の約束）は変えていません。`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT` は、ワザの共通の確認（番・段階・ねむり・マヒ・エネルギー）と、ワザの実装の `problem`・こんらんのダメージの確認がすべて通ったあとです。エンジンが止める `UNRESOLVED_…` は 15 件（v0.9 の 14 件 + 1 件）。

## 14. 変えたもの

| ファイル | 変更 |
|---|---|
| kyuura_engine/effects.py | 「はんげき」の判定と与える処理（6 章・11 章）、`AttackUse.counterattacks`、`DamageProfile`・`AttackEffect.damage_profile`、2 つのワザの実装、効果のあるワザの実装 9 種類の `finish_damage_elements`、回復の前の確認（`_skip_heal_of_knocked_out_attacker`）、登録（id `kyuura-engine-0.10`） |
| kyuura_engine/engine.py | ワザの宣言の前の C18 の確認、`resolve`・`resume` のあとの `finish_damage_elements`、不変条件の例外（`_counter_knocked_out_attacker_awaiting`）、説明の更新 |
| kyuura_engine/decisions.py | `push_attack_decision` の前の確認（与えていない「はんげき」がない） |
| kyuura_engine/__init__.py・pyproject.toml | `working_counterattack_power` を公開、版 0.10.0 |
| kyuura_engine/cards.py | 写しのプール `pool_v0_10` |
| scripts/extract_kyuura_cards.py・kyuura_engine/data/kyuura_cards.json | `POOL_V0_10`（ゴーリキー・カイリキー）・参照カード（サカキのカイリキー）。写しを作り直した（`--check` が kyuura `ecb2d694` と一致） |
| kyuura_engine/data/card_verification.json | PMCG1-055・PMCG1-057・PMCG6-061 の照合の記録 |
| tests/log_audit.py | 12.1 |
| tools/stress_engine.py | カイリキーの組（`machamp`・`machamp_mixed`）。`POWER_USERS` の最後にカイリキー（宣言の試み）。「はんげき」の観測（ワザの前の場からエンジンと同じ公開の問い合わせで求めて、ログと比べる） |

## 15. 変えなかったもの

- 書き出しの形式（9）・状態の項目・コマンド・段階・決定の種類。
- `engine._finish_attack`（きぜつ・サイド・交代・勝ち負け）・p.311 の表・サイドの正規化（v0.2f）。
- v0.5〜v0.9 の特殊能力（エナジートランス・あまごい・ダメージスワップ・かがくへんかガス・とうめい）と、その拒否のコード・ログ。
- 既存の未解決の裁定（v0.9 までの 14 のコード・コードのない T27）。R13・T19b・H4・K3 の扱い・拒否のコードの順番の保証しない範囲。
- 比較の駆動（tools/compat_driver.py）・参照データ（tests/fixtures/compat_base_4bd97bf.json・tests/fixtures/v0_1_reference.json）。

## 16. 変えた既存のテストと理由

| テスト | 変更 | 理由 |
|---|---|---|
| test_*_games（stage2・blastoise・alakazam・harden・evolution・bulbasaur・butterfree・muk・haunter）・test_rng_and_serialize・test_trainers・test_chemical_gas_v0_8・test_rain_dance_v0_6・test_damage_swap_v0_7 | 登録表の id を `kyuura-engine-0.10` に | 書き出しの `effects` の id が変わった（ルールの動き・乱数・ログは同じ） |
| test_pokemon_powers_v0_5 | パワーの一覧に「はんげき」、件数 6 | 登録を加えた |
| test_effects | 説明文のあるワザの一覧に PMCG1-055 の 2 件、件数 56、パワーの一覧 | 同上 |
| test_cards | `pool_v0_10`、使えるカード | 写しのプールを加えた |
| test_chemical_gas_v0_8 | 宣言しない特殊能力の一覧に `PowerKey("PMCG1-057", 0)` | 同上 |
| test_effect_preflight_v0_3d | `ATTACKS`・`EVOLVED_FROM` に 3 つのワザ | ワザの実装を加えたら `ATTACKS` に加える（CLAUDE.md） |
| test_unresolved_boundaries_v0_4e | `ALL_CODES` に新しいコード、`CounterattackDoubleKnockoutBoundaryTest` | 止める場合を加えた |

## 17. 次の版への提案（G。実装していない）

- 自動回復型・きぜつを取り消す特殊能力（サカキのカイリキーの［こんじょう］。ワザのダメージできぜつするときにコイン）: きぜつの判定の時点（ワザのあと）にはたらく。`_finish_attack` の判定の前に評価を加え、コインの順番（複数のポケモン）と、「はんげき」で同時にきぜつする場合を原典で確かめる。
- 回数の制限のある特殊能力（「自分の番ごとに1回」）: 回数を状態に持つ（書き出しの形式 10・不変条件。v0.6 の `energy_attached_by_powers_this_turn` と同じ形）。
- 期限のある特殊能力の抑止（まきちらせ！ベトベトガス・ふしぎなガス）: 期限を状態に持つ（形式 10。v0.8 の continuous-effects 6 章）。
- 複数のポケモンにダメージを与えるワザ（ベンチへのダメージ・じばく）: 受けるポケモンの選び方と計算（p.257）を原典で確かめ、C34・C35（複数の「はんげき」の順番）と T27（複数の「とうめい」のコインの順番）をワザの宣言の前に止める処理を加える。
- ほかの「ダメージを受けたとき」の特殊能力（［ショックボム］・［わるいねぞう］・［どくのたいえき］）とワザ（「こうらがえし」・「クロスカウンター」）: [post-damage-powers-v0.10.md](post-damage-powers-v0.10.md) 7 章の確認。「こうらがえし」の返すダメージはワザによるダメージ（p.89・p.321）で、「はんげき」とは計算が違う。
- C18 (b) の裁定: 当時の公式の Q&A・『ポケモンカード ファンクラブ』などの資料で、ワザによるきぜつと、それがはたらかせた特殊能力によるきぜつが同時かを確かめられれば、止める処理を決まった処理に置きかえる。
