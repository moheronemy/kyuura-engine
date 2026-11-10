# U7-5e: 宣言する特殊能力（UsePokemonPower）の候補・型ごとの宣言の入力・依存する段（v0.171）

U7-5 の計画（[legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md)）の 5 番目の単位です。採用済みの型ごとの入力の宣言（D-U75-INPUT-DECL）と、2〜3 段の依存する入力（D-U75-CHAINED）を実装し、既存の `UsePokemonPower` を公開の API（合法手 API・client_api）で送れるようにしました。

- 基点: `c207fd1`（U7-5d の最終コミット。main は `0c00b56` のままで、T-F1・U7-5c・U7-5d はまだ取り込まれていない）。作業ブランチ `claude/u7-5e-power`
- 実装していないもの: `CheckFaceUpDeckCard`（U7-5f）・カツラの 2 枚目（`AttachEnergy.energy2`。R-1）・自分のうらのバトル場のポケモンの宣言といっしょに選ぶもの（R-2）・自分のうらのカードの特殊能力
- GUI・renderer・kyuura・カードデータ・固定デッキ・3 つの規約集合・過去の参照データは変えていません

## 0. U7-5d の監査記録の訂正

[legal-actions-u7-5d](legal-actions-u7-5d.md) 4 章で、キョウの忍者ジムの v0.146 の new_game からの列（seed 1・17）を「双子」と書いていました。2 つの seed は別の対戦で、手札・場・山札の枚数が違い、本人の知識と公開の情報は一致しません。テストが比べたのは `use_stadium` の候補（番号と場のスタジアムのカードを除く）・入力・入力の検査の応答だけです。

- 双子ではなく、別の対戦による合法な到達例として、U7-5d の文書・テストの説明・テストの名前（`test_legal_reach_examples_from_new_game`）を訂正しました
- 配分だけを変えた本当の双子は、構築盤面（`swap_hidden`）の組です（変えていない）
- `check_activation` が呼ぶ別のモジュールの関数の深い部分は、未確認のままです
- `may_stop_later` は受理のあとを評価していないことを示す区分で、候補の作成の情報の安全を保証する分類ではありません

## 1. 対象と、全入力経路の分類

`UsePokemonPower` の項目は `player`（主体）・`pokemon`（使うポケモン）・`power`（特殊能力の位置）・`energy`・`source`・`target`・`card`（特殊能力を印刷したカード）の 7 つです（`dataclasses.fields` で確かめた）。

- 使うポケモンと特殊能力（`pokemon`・`power`・`card`）は、候補が決めます。特殊能力の位置ごとに 1 つの `use_power` 候補を作ります（`powers_of` の位置。「ばける」でのせたカード・［へんしん］の写しを含む）
- 宣言といっしょに指定する項目（`energy`・`source`・`target`）は、型ごとの宣言の段です（3 章）
- コインの結果・受理のあとに選ぶもの（回復するポケモン・のせるカードなど）は、既存の決定です（`answer_decision`）。宣言の前へ移していません

登録の特殊能力の型の分類（コードで照らした。`effects.POWER_INPUT_STAGES`・`POWER_NOT_BY_COMMAND`）:

| 分類 | 型 | 候補 |
|---|---|---|
| UsePokemonPower で使う（宣言の入力あり） | 11 の型（下の 8 通りの形） | 段のある候補 |
| UsePokemonPower で使う（宣言の入力なし） | 45 の型 | 入力のない候補（`choices: []`） |
| 宣言するが UsePokemonPower で使わない（反応・ワザといっしょに使う力） | 11 の型と、`EntryPower`・`TriggeredPower` の部分型 | 候補にしない（既存の決定・ワザの宣言で答える） |
| 宣言しない（常にはたらく・自動的にはたらく） | `declared` が偽 | 候補にしない |
| 登録のない特殊能力 | — | 止める候補（`not_implemented`。入力なし） |
| 宣言のない型（今の登録にはない） | — | 入力の形を推測しない（`not_implemented`・`unconfirmed`） |

宣言の入力の形（設計の 9 通りの表と同じ。登録で UsePokemonPower を使う 56 の型と、宣言の表が一致することをテストが確かめる）:

| 形 | 段（選ぶ順） | 型 |
|---|---|---|
| E(attached)+S(own)+T(own) | 1 `source`（自分の場）→ 2 `energy`（その source についているカード）→ 3 `target`（自分の場） | `EnergyTransfer`（エナジートランス）・`MoveEnergyAmongNamed` |
| E(attached)+S(own) | 1 `source` → 2 `energy`（source についているカード） | `TakeEnergyToSelf`・`ConvertBasicEnergyColor` |
| E(hand)+T(own) | 1 `energy`（本人の手札）→ 2 `target`（自分の場） | `AttachEnergyFromHand`（あまごい） |
| E(hand) | 1 `energy`（本人の手札） | `DiscardTypeEnergyFromHand` |
| S(own)+T(own) | 1 `source` → 2 `target`（どちらも自分の場） | `MoveDamageCounter`（ダメージスワップ） |
| S(opp)+T(opp) | 1 `source` → 2 `target`（どちらも相手の場） | `MoveOpponentDamageCounter`（のろい） |
| S(own) | 1 `source`（自分の場） | `MoveDamageCounterToSelf`・`MoveGroupCounterToSelf` |
| T(opp bench) | 1 `target`（相手のベンチ） | `StopOpponentBenchPowersThisTurn`（じっとみる） |
| none | なし | 45 の型 |

- どの段も 1 つを選びます（任意の段はない。使わないことは宣言しないこと）。並びは段の順のまま送ります
- 回数の制限（「自分の番ごとに1回」）・特殊状態・消す効果（かがくへんかガスなど 6 つ）・写した特殊能力（TF1・SV3）・DV3 は、エンジンの確かめのとおりです。ゲーム上できない（`IllegalActionError`）なら候補・組を作らず、未裁定・未対応なら示して実行できない区分にします

## 2. 共通にした確かめと、維持した実行時の処理

`engine._use_pokemon_power` の宣言の前の部分を `engine.check_use_pokemon_power(state, cmd, *, use_condition=True)` に移しました。順番・停止コード・理由の文は同じで、副作用はありません。`use_condition=False` は特殊能力ごとの `check_usable` だけを呼ばない指定で、エンジンの処理はいつも真で呼びます。

- 候補の作成は、使う特殊能力の段の確かめ（`use_condition=False`）と、宣言の入力の組ごとの確かめ（真）を呼びます。`apply_command`・効果の処理・先読みは呼びません
- 実行時に残すもの: コマンドの入口の、うらのカードをおもてにする処理（`_reveal_for_action`。F-5）と、本当のカードによらない拒否にそろえる試行（`_identity_independent`）、コマンドの終わりの確かめ（MH1 など）、効果の処理・コイン・あまごいの反応・きぜつ・空いたバトル場の交代

## 3. 型ごとの宣言の入力と、3 段の依存する入力

### 3.1 宣言（`effects.POWER_INPUT_STAGES`）

- 実装の型そのものを鍵にした表（継承した型は、表に書くまで宣言がない）。値は段ごとの (コマンドの項目, 選べるものの場所)
- 選べるものの場所は 5 つ: `own_pokemon`・`opponent_pokemon`・`opponent_bench`・`energy_on_source`（前の段の source についているカード）・`hand_card`（本人の手札）
- カード名・カード ID・モードの名前による分岐はありません。表にない型・知らない場所は、入力の形を推測しません
- テストが確かめること: 宣言の項目が `check_usable` の読む項目に含まれ、宣言しない項目を読むのは指定を拒否するためだけ。代表の組で、候補どおりのコマンドが直接のコマンドと同じ結果

### 3.2 依存する段（契約 `kyuura-client-api` 形式 1 への追加）

U7-3 の 2 段（`depends_on_stage`・`options_by_choice`）を、意味を変えずに延ばしました。

- 2 段目以降の選ぶものの番号は、前のすべての段の選び方ごとに別の番号です。選ぶものに `after`（直前の段の選ぶものの番号）を加えました
- 段に `upstream_stages`（前のすべての段の番号）を加えました。`depends_on_stage` は直前の段、`options_by_choice` は直前の段の番号ごとの選べるもの（U7-3 と同じ意味）
- 直前の段の番号が、前のすべての段の選び方を識別します。異なる上流の選び方の番号を混ぜた入力・段の並びの違う入力・数の違う入力は `CANDIDATE_INPUT_INVALID` で拒否します
- 組み合わせの全部（全段の直積）は並べません。並べるのは、確かめを通った組の前の段の選び方ごとの続きだけです
- 入力を変えたときに無効にする範囲: k 段目を変えたら、k+1 段目以降の選び方と、それまでの入力の検査（`check`）の結果は無効です（番号が別になるので、古い番号は新しい k 段目の `options_by_choice` にない）
- `stage_dependency_problems` が、段の番号の並び・直前の段への依存（循環・前でない段）・存在しない参照・`after` と `options_by_choice` の食い違いを見つけます
- 古いクライアント: `depends_on_stage`・`options_by_choice` の意味は U7-3 と同じです。項目の一覧で知らない項目を止めるクライアント（GUI の契約の表の `stage_keys`）は、`upstream_stages`・`after` を知るまで「不明な応答」として止めます（安全な側の失敗）。既存の項目の意味を変えていないので、形式の版は 1 のままです
  - 訂正（CORR-3。[legal-actions-u7-5fg-spec](legal-actions-u7-5fg-spec.md) 0.2 節）: v0.171 では「新しい項目を無視するクライアントは、直前の段の番号で引けば正しい組だけを選べます」と書いていました。成り立つのは、各段の `depends_on_stage` が指す段の選ぶもので `options_by_choice` を引くクライアントだけです。U7-3 の 2 段を前提に 1 段目で引くクライアントは組が作れず（閉じた側の失敗）、`options_by_choice` を使わないクライアントの安全はサーバの入力の検査によります（小さな既知の入力で確かめた）

## 4. 情報源と、E 群・F-4・F-5 の結論

- 候補・inputs・check は、本人の知識と公開の情報だけを使います。状態・乱数・ログを変えないことをテストで確かめました
  - 選べるものは、場のポケモン（公開）、ついているカード（公開）、本人の手札
- 相手のうらのカード: 公開された位置（場のポケモンの番号・場所）と `face_down` だけを示します。カードの uid・カード id・名前・結果の予告を出しません
  - 指定する組（source・target・energy のついているポケモンがうらのカード）は、エンジンがおもてにしてから確かめる（F-5）ので、候補では確かめず `unverified`（理由 `face_down_reveal_not_evaluated`）にします
- 状態の複製の上で効果を試す 7 の実装（UP-5t。`ChooseFossilEvolvedThenCoinDevolveAll`・`CoinConditionOnEitherActive`・`ReturnActiveToHandWithBenchLetters`・`Shapeshift`・`StopOpponentBenchPowersThisTurn`・`SwitchOpponentChosenByOpponent`・`SwitchOpponentOnHeads`）
  - パッケージ全体の呼び出しを、名前で解決してたどりました（外部の関数の 1 段目で止めていない）
    - 素の名前・import した名前・`self` のメソッド・モジュールの関数を解決し、多態で呼ぶ効果のフック（`hp_bonus`・`units`・`is_able`・`status_allows`・`note_switch`・`located`・`energy_role`・登録の照合 `check` など）は、同じ名前の実装をすべて根に加えました（閉包は 955 の関数）
  - 読む秘密の場所は、本人の手札の進化カード（本人の知識）だけでした。山札・サイド・置いておくカード・乱数・うらのカードの集合は読みません（複製の上の、手札・山札への書き込みはある）
  - 名前で解決できない呼び出し（状態のメソッド `card_def`・`find_pokemon`・`clone` など、登録表の引き、正規表現）は残ります。うらのカードの定義の読みは、本当のカードによらず FD1 です
  - この結果で、候補の作成で呼びます。複製の上の試行であることを、安全の根拠にはしていません
  - 同じ走査で、U7-5c の場の試行 6 つ（`state_stop_after`・`switch_max_hp_drop_check`）も秘密の場所を読まないことを確かめました（U7-5c の 1 段目までの判断を、深い走査で補った）
  - U7-5c の山札から引いて試す 5 つ（PT-5e）は、別の監査の課題のままです（今回は依存しない）
- 持ち主の知識の関数を呼ぶ 4 の実装（UP-5o）は、そのまま呼びます。実際の山札を読む判定には戻していません
- F-4（相手のうらのカードの項目を読む確かめ）: 相手のベンチのうらのカードの本当のカードだけが違う双子（ディグダ・ユンゲラー）で、モルフォンの［へんしょく］はどちらも FD1 で止まり、候補（`unresolved_ruling`・実行できない区分）・入力・応答は同じでした。本当のカードによらない保守的な停止で、漏れではありません（止め方は変えていない）
- F-5（入口のおもてにする処理の順）: 候補はこの順を写さず、指定するうらのカードを含む組を `unverified` にします

## 5. 処理可能性・coverage・既存の挙動との一致

- 特殊能力の候補は `supported` にしません（`may_stop_later`。理由 `continuation_not_evaluated`）。処理可能性（`unverified` など）と入力の公開（`input_disclosure`）は別の軸です。選べるものは公開の値と本人の手札だけで作るので `confirmed`、入力のない候補は `no_input`、宣言のない型は `unconfirmed`
- coverage: 番の操作の `not_covered_kinds` は `check_face_up_deck` だけになりました。`completeness` は `partial` のままです
  - 残る経路: R-1（カツラの 2 枚目）、R-2（自分のうらのバトル場のポケモンの宣言といっしょに選ぶもの）、自分のうらのカードの特殊能力（候補にしない）
- U7 経由・client_api 経由・直接のコマンドで、結果・状態・乱数・ログ・診断が一致することを確かめました
  - 3 段: エナジートランス
  - 2 段: あまごい、ダメージスワップ、のろい（相手の場）、ほのおをもらう（new_game からの列）
  - 入力なし: ラフレシアのヒーリング（コインの両面・受理のあとの決定・番ごとに 1 回）
  - 写した特殊能力: メタモンが写したエナジートランス（印刷したカードは相手のバトル場のカード）
- エンジンの動作は変えていません。意図した差: 既存の U7 のテスト（U7-1・U7-3・U7-4・U7-5a＋b・U7-5c・U7-5d）の coverage の期待から `use_power` を外しました。U7-5 の設計のテストの、壊して確かめる対象の単位を U7-5g に移しました

## 6. client_api と取っ手

既存の `candidates`・`inputs`・`check`・`submit` をそのまま使います。主体の固定、ホストの入口との分離、受理による取っ手の失効、拒否でほかの主体の取っ手を失効させないこと、古い取っ手・別の主体・別の対戦の拒否、拒否を相手・観戦者へ知らせないこと、通常の応答に検証者の情報・生の例外の文・完全な状態を出さないことは、U7-5c・U7-5d と同じです。

## 7. GUI への引き継ぎ（GUI リポジトリは変更していない）

- 比べる相手（2026-11-08 に読み取りだけで確かめた）: GUI の最新の作業ブランチ `feature/engine-u7-4-attacks` の `3649946`（エンジン `9506d63`・0.166.0 を固定）。GUI の `main` の `7660ab4` はエンジン `d0c5cfa`（v0.164）を固定
  - v0.172: 自分のうらのカードの特殊能力は、U7-5g-2 で 0・1 段の型を本人の候補に加えました（[legal-actions-u7-5fg](legal-actions-u7-5fg.md) 4 章）。GUI の比べる相手は main の `088822c`（エンジン `74c8e1f`・0.171.0）です
  - 訂正（CORR-3）: 上は古い比べる相手でした。最新の公開の作業ブランチは `feature/engine-u7-5-trainers-stadium` の `9c36a8f` で、エンジン `0885d66`（0.170.0）を固定しています（[legal-actions-u7-5fg-spec](legal-actions-u7-5fg-spec.md) 0.1 節）。0.170.0 からの差は、この章の `use_power` の項目です
- 固定して導入を確かめた完全なコミットと版: `kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@74c8e1f8ca03d017d5c0a8a79e6fdaa33d25b7f8`（版 0.171.0。9 章）。GUI の固定を 0.166.0 からこのコミットに更新すると、U7-5a〜U7-5e の差がまとめて入る
- 0.170.0 からの差（U7-5a〜U7-5d の差は [legal-actions-u7-5d](legal-actions-u7-5d.md) 8.2 節）
  - 新しい候補の種類 `use_power`（特殊能力の位置ごとに 1 つ。同じ種類の候補がいくつもある）
  - 候補の項目 `pokemon`（使うポケモン。U7-5a の場のポケモンの形）・`power`（`index`・`name_ja`・`card`・`card_id`。印刷したカード）
  - 段の role `source`・`energy`・`target`、段の項目 `upstream_stages`、選ぶものの項目 `after`
  - 相手のうらのカードの選ぶものは `pokemon`・`zone`・`bench_index`・`face_down` だけ（`card`・`card_id` がない）
- GUI の型・検証・表示に必要な変更（GUI を動かしていないので、対応を保証しない）
  - 契約の表の `implemented_kinds`・`gui_operable_kinds` に `use_power`、`stage_keys` に `upstream_stages`、選ぶものの項目に `after` を加える
  - 3 段の画面: 直前の段の選ぶものの番号で `options_by_choice` を引き、選んだら次の段を出す。前の段を変えたら、あとの段の選び方と検査の結果を消す
  - 入力のない `use_power` は `choices: []` で送る
  - 受理のあとは `refetch_required` で候補を取り直し、`answer_decision`（回復するポケモンなど）に答える

### 7.1 3 段の JSON の例（エナジートランス。client_api の実際の応答から、一部の選ぶものと保証の文を除いた）

```json
候補: {"id": "c3", "kind": "use_power", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"],
       "pokemon": {"pokemon": 1, "card": 2, "zone": "active", "card_id": "PMCG1-011"},
       "power": {"index": 0, "name_ja": "エナジートランス", "card": 2, "card_id": "PMCG1-011"},
       "choices_format": "[source の番号, energy の番号, target の番号]（段の順）", "input_disclosure": "confirmed",
       "input_stages": [{"stage": 1, "input": "choose_option"}, {"stage": 2, "input": "choose_option"}, {"stage": 3, "input": "choose_option"}]}
1 段目: {"stage": 1, "role": "source", "meaning": "pokemon", "count": {"min": 1, "max": 1},
         "options": [{"id": "o1", "pokemon": 1, "zone": "active", "card_id": "PMCG1-011", …}, {"id": "o2", "pokemon": 2, "zone": "bench", "bench_index": 0, …}]}
2 段目: {"stage": 2, "role": "energy", "meaning": "card", "depends_on_stage": 1, "upstream_stages": [1],
         "options": [{"id": "o3", "card": 3, "card_id": "PMCG1-097", "after": "o1", …}, {"id": "o4", "card": 4, "card_id": "PMCG1-097", "after": "o1", …}],
         "options_by_choice": {"o1": [{"option": "o3", "eligible": true, …}, {"option": "o4", "eligible": true, …}], "o2": [{"option": "o5", …}]}}
3 段目: {"stage": 3, "role": "target", "meaning": "pokemon", "depends_on_stage": 2, "upstream_stages": [1, 2],
         "options": [{"id": "o6", "pokemon": 2, "zone": "bench", "after": "o3", …}, {"id": "o7", "pokemon": 3, "zone": "bench", "after": "o3", …}, …],
         "options_by_choice": {"o3": [{"option": "o6", …}, {"option": "o7", …}], "o4": [{"option": "o8", …}, …], "o5": [{"option": "o10", …}, …]}}
{"type": "check", …, "candidate": "c3", "choices": ["o1", "o3", "o6"]} → {"valid": true, "refusal": null}
{"type": "check", …, "candidate": "c3", "choices": ["o2", "o3", "o6"]} → {"valid": false, "refusal": {"code": "CANDIDATE_INPUT_INVALID", …}}（o3 は o1 のあとの番号）
```

- 拒否と受理のあとの停止の区別は U7-5c・U7-5d と同じ（ホストの段の `refused`・エンジンの `rejected`・受理のあとの `status`・`next`）

## 8. 未確認・未対応

- 名前で解決できない呼び出し（状態のメソッド・登録表の引き・正規表現）の先（UP-5t の走査の限界）
  - 追記（v0.177 のあと）: 静的な監査を [legal-actions-up5t-audit.md](legal-actions-up5t-audit.md) にまとめた。4 章の「うらのカードの定義の読みは、本当のカードによらず FD1」は、`CoinConditionOnEitherActive` の試行が相手のうらの対戦ポケモンを `designate_face_down`（`printed_def`）で読む経路を除く（候補の側の保護がない。監査の 3.1 節）。955 の閉包の走査は保存されていない
- U7-5c の山札から引いて試す 5 つ（PT-5e）の読む値
- 自分のうらのカードの特殊能力（候補にしない）・R-1・R-2（U7-5g）・`CheckFaceUpDeckCard`（U7-5f）
- GUI の画面での 3 段の入力は確かめていません

## 9. 確かめたこと

限定の範囲です。全体のテスト・状態の監査・108 のバッチ・4,356 局・lockstep の全体・広いストレステストは流していません。

- **テスト**: 1 モジュールずつ別のプロセスで、並列にしないで流しました（2026-11-08。開始・終了・件数・終了コードを実行ごとに保存）。27 対象・739 件（`test_legal_actions_u7_5e` は直したあとの再実行の 24 件で数える）、すべて成功・終了コード 0・skip 0
  - 新しい `tests/test_legal_actions_u7_5e.py`: 24 件
    - 1 回目の実行で 1 件が失敗しました（メタモンの写した特殊能力の盤面が、相手が 2 進化できない番の構築で、エンジンの不変条件が `failed` にした）。テストの盤面の誤りで、番を直して 24 件が成功
    - コードの上の網羅（補助関数）: 宣言の表と登録の 56 の型・設計の 9 通りの表・`check_usable` の読む項目の対応、依存する段の確かめが壊した段を見つけること、`check_use_pokemon_power` とコマンドの処理の拒否の一致
    - 構築盤面: 3 段（エナジートランス）・2 段（あまごい・ダメージスワップ・のろい）・入力なし（ヒーリング。コインの両面・受理のあとの決定・番ごとに 1 回）・上流を混ぜた入力と古い下流の入力の拒否・ねむり・かがくへんかガス・写した特殊能力（メタモン）・「ばける」・相手のうらのカードの双子（F-4）・取っ手・不正な入力・状態の不変・client_api
    - new_game からの合法な操作の列（固定の seed 1。3 つの規約集合）: 準備 → `attach_energy` → `use_power`（ほのおをもらう。2 段）→ 番を終える。直接の列と同じ状態、完全な再現用記録の収集・U4 の再実行（`succeeded`）・閲覧用記録の構造
  - U7: `u7_5d` 25・`u7_5c` 32・`u7_5_design` 27・`u7_1` 42・`u7_2` 17・`u7_3` 29・`u7_4` 27・`u7_5ab` 27・`api_design` 13・`decision_audit` 15・`client_api` 9
  - 特殊能力の既存のテスト: `pokemon_powers_v0_5` 21・`rain_dance_v0_6` 37・`damage_swap_v0_7` 37・`chemical_gas_v0_8` 26・`power_decisions_v0_42` 58・`virtual_attacks_transformation_v0_49` 58・`secret_plan_v0_67` 24
  - T-F1・F-8: `chaos_gym_borrow_t_f1` 12・`stadium_reuse_special_energy_v0_58` 41
  - 記録・再実行・閲覧用記録・保存と復元: `replay_record_v0_153` 25・`replay_run_v0_154` 23・`view_record_v0_155` 24・`state_snapshot_v0_157` 37・`snapshot_replay_v0_158` 28
  - 版: `test_preset_decks_v0_20` の `StartGameTest.test_version` 1
- **生成物・データの検査**: `scripts/build_*.py --check` の 11 個と、`check_implementation_assumptions --check`・`check_normalization_revalidation --check`・`check_card_sources`・`check_research_links` は終了コード 0
  - 停止の台帳は作り直して、`engine.py` の行番号だけが変わりました（10 行）
  - `check_implementation_assumptions --sites` の出力は基点 `c207fd1` と同じ（56 行）
- **lint**（ruff 0.17.2）: 新しいファイル・`legal_actions.py`・U7 のテスト・U7-5 の生成器は指摘なし。`engine.py`・`effects.py` の指摘の数は基点と同じ
- **配布と通常のインストール**（コミット `74c8e1f8ca03d017d5c0a8a79e6fdaa33d25b7f8`。版 0.171.0）
  - `git archive` の木から作った wheel・sdist の中身の検査（`scripts/check_distribution.py`）: required=62・problems=0
  - クリーンな仮想環境に、Git の URL から通常のインストール（編集可能なインストール・PYTHONPATH なし）。`direct_url.json` のコミットが一致
  - リポジトリの外から `python -I` でスモークテスト。問題 0
    - 確かめたもの: site-packages からの読み込み・全サブパッケージ・3 つの規約集合の照合値・初期配置・番の操作・ワザの宣言・`discard_from_play`・`play_trainer`・錯乱ジムの相手の答え・`use_stadium`
  - client_api の `use_power`: ロケット団のヒトカゲの［ほのおをもらう］（`source` → `energy` の 2 段。2 段目の `upstream_stages` は `[1]`）
    - ほかの上流の番号を混ぜた入力は `CANDIDATE_INPUT_INVALID`、正しい組は検査が有効で受理。炎エネルギーがヒトカゲに移った
    - 1 回目のスモークでは、スモークの準備（初期配置でバトル場の 1 匹だけを置く）で場にポケモンが 2 匹そろわず、この確かめに届きませんでした。スモークの側で client_api の `play_basic` でベンチに出すように直して成功（エンジンは変えていない）
  - 実装の識別の `behavior_digest` は、インストールしたものとソースの木で同じ（`e87cafea9b2ee323893ae665cf851f00fe4ffce6244fdd68568b5e13e94932fb`）
