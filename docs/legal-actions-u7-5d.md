# U7-5d: 場のスタジアム（UseStadium）の候補・入力・検査・送信（v0.170）

U7-5 の計画（[legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md)）の 4 番目の単位です。U7-5c（[legal-actions-u7-5c](legal-actions-u7-5c.md)。手札のトレーナー）に続いて、場のスタジアムの「自分の番に使ってよい効果」（既存の `UseStadium`）を、公開の API（合法手 API・client_api）で送れるようにしました。

- 基点: `13249d0`（U7-5c の最終コミット。main は `0c00b56` のままで、T-F1・U7-5c はまだ取り込まれていない）。作業ブランチ `claude/u7-5d-stadium`
- 実装していないもの: 特殊能力（`UsePokemonPower`。U7-5e）・`CheckFaceUpDeckCard`（U7-5f）・カツラの 2 枚目（`AttachEnergy.energy2`。R-1。U7-5g）・3 段の入力の基盤
- GUI・renderer・kyuura・カードデータ・固定デッキ・3 つの規約集合・過去の参照データは変えていません

## 1. UseStadium の入力と、登録したスタジアムの効果

`UseStadium` の項目は `player`（使うプレイヤー。主体で、取っ手が決める）と `energy`（`int | None`。既定は None）の 2 つです（`dataclasses.fields` で確かめた）。手札からスタジアムを出す操作は `PlayTrainer`（U7-5c の `play_trainer`）で、別の操作です。

- 使う主体: 番のプレイヤー（`require_turn`。段階 `MAIN`）。場のスタジアムの持ち主でなくても使えます。持ち主でも、番でなければ使えません
- 回数の記録: 使ったプレイヤーとスタジアムのカードの組（`stadium_uses_this_turn`）。コインが「うら」でも使ったことになります

登録したスタジアムの型は 24 です。候補は、使ってよい効果の登録（`StadiumEffect.activated`）から作ります。スタジアムが場にあるだけでは作りません。

| 型 | カード | 宣言の入力（`energy`） | 回数 | 受理のあと | 使う前の止め方（例） |
|---|---|---|---|---|---|
| `CureByDiscardingEnergyStadium` | タマムシシティジム | 必須: 自分の「エリカのポケモン」についているエネルギーカード 1 枚（種類を問わない） | なし | なし（トラッシュして回復） | TG1（特殊状態がない）・STB1 |
| `ReturnBasicEnergyStadium` | ヤマブキシティジム | 必須: 自分の「ナツメのポケモン」についている基本エネルギーカード 1 枚 | なし | なし（手札に加える。MH1 はコマンドの終わり） | RB3（レインボーエネルギー）・STB1 |
| `CoinReturnOwnerPokemonStadium` | セキチクシティジム | なし | 番ごとに 1 回 | コイン →「おもて」なら自分の「キョウのポケモン」を選ぶ決定 → 空いたバトル場 | FG1・FG2・SX2・NT2・AL2・STB1 |
| `CoinDrawStadium` | ラッキースタジアム | なし | 番ごとに 1 回（PRN-027 は書かれていない） | コイン →「おもて」なら 1 枚引く | LK1（PRN-027 の同じ番の再使用）・RS1・STB1 |
| `CoinRetrieveBasicEnergyStadium` | エネルギースタジアム | なし | 番ごとに 1 回 | コイン →「おもて」ならトラッシュの基本エネルギーを選ぶ決定 | EN1（トラッシュにない）・RS1・STB1 |
| `CoinBenchOwnerBasicFromDeckStadium` | キョウの忍者ジム | なし | 番ごとに 1 回 | コイン →「おもて」なら山札のキョウのたねポケモンを選ぶ決定 | NJ1（4 章）・GG1・RS1・STB1 |
| `CoinHealOwnActiveStadium` | いやしの野原 | なし | 番ごとに 1 回 | コイン →「おもて」なら回復 | HF1（傷のない対戦ポケモン）・RS1・STB1 |
| `LookDeckTopStadium` | ラジオとう | なし | 番ごとに 1 回 | 見る枚数の決定など | RS1・STB1 |
| ほかの 16 の型（クチバシ・錯乱ジム・リムーブ禁止ジムなど） | — | — | — | — | 常時の効果だけ。候補を作らない（エンジンも `STADIUM_NOT_USABLE` で受け付けない） |

- 選ばせるものの形は、型の宣言 `StadiumEffect.energy_choice` から作ります（v0.170 で加えた最小の入力の宣言。エンジンの挙動は変えない）
  - None なら選ばせない（`energy` を指定すると `STADIUM_CHOICE_NOT_USED`）
  - `own_attached`（`ENERGY_CHOICE_OWN_ATTACHED`）なら、使うプレイヤーの場のポケモンについているエネルギーカード 1 枚（指定しないと `STADIUM_CHOICE_REQUIRED`）
  - 宣言と `check_activation` が食い違わないこと、宣言が設計の選ばせるものの形の表（`stadium_shapes`）と同じことを、登録したすべての型でテストが確かめます
- コインの結果は入力させません。受理のあとの選ぶもの（ポケモン・エネルギー・山札のカード・見る枚数）は、すべて受理のあとの既存の決定です
- カード名・カード ID による共通処理の分岐は加えていません

## 2. 候補の形

- 選ばせるもののない効果: 入力のない候補（`input_disclosure: "no_input"`・`input_stages: []`・`choices_format: "[]"`）。送るときの `choices` は空
- エネルギーを選ばせる効果: 1 段の `choose_option`（`role: "energy"`・`meaning: "card"`・`count` 1〜1・`order: "not_applicable"`）
  - 選べるものは、本人の場のポケモン（バトル場 → ベンチ）についているエネルギーカード（公開）のうち、エンジンの確かめを通ったもの
  - 項目は `card`・`card_id`（エネルギーカード）と `holder`（ついている本人の場のポケモン。U7-5a と同じ形の `pokemon`・`card`・`zone`・`bench_index`・`card_id`。うらのカードは `face_down` で示し、`card_id` を出さない）
- 候補には `stadium`（場のスタジアムの `card`・`card_id`・持ち主 `owner`。公開）を加えます
- ゲーム上できない場合（場にスタジアムがない・使ってよい効果がない・同じ番の 2 回目・選べるエネルギーがない）は、候補・選べるものを作りません
- 未裁定・未対応（`UnsupportedError`）は、候補・選べるものとして示し、実行できない区分にします（送る前に `CANDIDATE_NOT_EXECUTABLE`）
- 候補の並びは `MAIN_KINDS` の順（`play_trainer` のあと、場のポケモン 1 匹を指す操作の前）。`implemented_kinds` では最後に加えました

## 3. 共通にした確かめと、情報源

`engine._use_stadium` の使う前の部分を `engine.check_use_stadium(state, cmd)` に移しました。判定の順番（番・段階 → 場のスタジアム `NO_STADIUM` → 実装の `check_activation`）、停止コード、理由の文は同じで、副作用はありません。`_use_stadium` はこれを呼んでから使います。

- 候補の作成・入力の検査は、同じ `check_use_stadium` を呼びます。`apply_command`・効果の試行・先読みは呼びません
- 使える 8 の実装の `check_activation` の呼び出しの閉包（effects.py の中）を走査しました。どれも状態の複製（`.clone`）を呼ばず、U7-5c の場の試行（`state_stop_after`・`switch_max_hp_drop_check`）にもつながりません。U7-5c の E 群の判断に依存しません
  - 読むのは、番、場のポケモン（今の姿の名前・ついているカード・特殊状態・ダメージ）、トラッシュ、回数の記録（`stadium_uses_this_turn`・同じ名前の使用の記録）、トレーナーの使用の禁止（場の力・期限のある禁止）、ベンチの空き
  - うらのカードの定義を読むと、本当のカードによらず FD1 で止まります（セキチクシティジムの F-3）
  - 副作用がないことを、安全の根拠にはしていません
- キョウの忍者ジムだけが、持ち主の知識の関数（A-own）を使います（4 章）
- 実行時に残すもの（候補の作成では評価しない）
  - コマンドの終わりの確かめ（`_apply_once`。MH1・決められない姿・SC2 など。ヤマブキシティジムでナツメのゴースの［ガスのからだ］が下がる場合など）
  - コインと効果の処理、空いたバトル場の勝ち負け・交代（`resolution.after_stadium`）

## 4. キョウの忍者ジム（持ち主の知識の下限）

v0.146（[play-set-verification-v0.146](play-set-verification-v0.146.md) 3 章）の判定を、そのまま使います。実際の山札を読む判定には戻していません。

- 山札に選べるカードがあることを、配分を読まない下限（`deck_target_lower_bound`）で確かめます
  - 下限 = 本人に見えないキョウのたねポケモンの数 − 山札の外の見えないカードの数（うらのサイド・持ち主に見えない置いておくカード）
  - おもてのサイドと、本人が知っているカード（手札・場・トラッシュ）は、見えないカードに数えません
  - 下限が 1 より小さければ NJ1（`unresolved_ruling`）で止めます。山札にあるかもしれないことと、あると保証できることを分けた、保守的な停止です
  - 例: サイドがうらの 6 枚なら、キョウのたねポケモンが 7 枚以上ないと NJ1 です（6 枚が全部山札にあっても止める）。この停止を緩める規約は加えていません
- ベンチに出しても止めない（GG1）カードがあることも、配分を読まない下限（`bench_entry_unconfirmed`）で確かめます
- 実際の山札を直接たどるのは、山札と見えないほかの場所を合わせた集合の、エンジンの不具合の確かめ（`placed_entry_power_guard`）だけです。配分によらず、結果は内部の不具合の例外だけです
- 「おもて」で正当に検索が始まったあとの選ぶもの（決定）は、実際の山札のカードです
- 双子（山札とサイドの配分だけを変えた構築盤面: キョウのドガース 1 枚・7 枚。v0.146 の new_game からの列: seed 1 は山札、seed 17 はサイド）で、候補・入力・件数・並び・理由・不正な入力への応答が一致することを確かめました

## 5. 処理可能性と coverage

- 区分は既存の 6 つのままです。スタジアムの候補は `supported` にしません（`may_stop_later`。理由 `continuation_not_evaluated`）。場にスタジアムがあるので、U7-3 の supported の条件（受理のあとの反応・決定のもとが場にない）を満たしません
- 入力の公開（`input_disclosure`）は別の軸です。選べるものは公開の値（場のポケモンについているカード）と本人の場だけで作るので `confirmed`。選ばせるもののない効果は `no_input`
  - 知らない選ばせるものの宣言（今の登録にはない）は、入力の形を作らず `unconfirmed`・`not_implemented` にします
- coverage: 番の操作の `not_covered_kinds` から `use_stadium` が外れ、`use_power`・`check_face_up_deck` が残ります。`completeness` は `partial` のままです
  - 残る経路: R-1（カツラの 2 枚目の「炎」エネルギー。U7-3 の attach_energy が使わない）、R-2（自分のうらのバトル場のポケモンの、宣言といっしょに選ぶもの。U7-4 は示さない）
  - coverage の項目の意味・並び（`scope_kinds` は `MAIN_KINDS` の順）は変えていません

## 6. 既存のエンジンとの一致と、意図した差

- U7 経由・client_api 経由・直接のコマンドで、受理・拒否の結果、状態・乱数・ログ、送り手への診断が一致することを確かめました
  - ラッキースタジアム（コインの両面）、エネルギースタジアム（「おもて」の決定）、セキチクシティジム（「おもて」の決定と空いたバトル場）、タマムシシティジム、ヤマブキシティジム、キョウの忍者ジム（「おもて」の検索）
- エンジンの動作は変えていません（`_use_stadium` の前半を関数にし、型に入力の宣言を加えただけ）
- 意図した差: 既存の U7 のテスト（U7-3・U7-4・U7-5a＋b・U7-5c）の coverage の期待から `use_stadium` を外しました。U7-5 の設計のテストの、壊して確かめる対象の単位を U7-5d から U7-5e に移しました

## 7. client_api と取っ手

既存の `candidates`・`inputs`・`check`・`submit` をそのまま使います（契約 `kyuura-client-api`・形式 1、合法手 API の形式 1 は変えていない）。U7-5c と同じ約束です。

- 主体は入口で固定します。ホストの操作（ジャンケンの結果・延長戦の開始）とは別の入口です
- 受理でその対戦の取っ手をすべて失効させ、拒否ではほかの主体の取っ手を失効させません
- 古い取っ手・別の主体・別の対戦を拒否します。拒否の存在を相手・観戦者へ知らせません
- 通常の応答に、検証者の情報・生の例外の文・完全な状態を出しません

## 8. GUI への引き継ぎ（U7-5a〜U7-5d をまとめた追従。GUI リポジトリは変更していない）

### 8.1 比べる相手（2026-11-08 に読み取りだけで確かめた）

- 公開されている GUI の最新の作業ブランチ: `feature/engine-u7-4-attacks` の `3649946`。エンジン `9506d63`（版 0.166.0）を固定
  - GUI の `main`（`7660ab4`）はエンジン `d0c5cfa`（v0.164）を固定しています
- GUI の契約の表（`contract/kyuura-client-api-v1.json`）は、`implemented_kinds`・`gui_operable_kinds`・`stage_keys`・選べるものの項目・`reason_codes` を列挙し、知らない値・項目を「不明な応答」として操作を止めます
- 導入を確かめた完全なコミットと版: 9 章のあとの文書だけのコミットで記録します

### 8.2 0.166.0 からの差（GUI の型・検証・表示に必要な変更）

| 版 | 新しい候補の種類 | 段の role | 新しい項目・値 |
|---|---|---|---|
| 0.167.0（U7-5a＋b） | `remove_disguise`・`discard_from_play`・`reveal_face_down` | `disguised`・`discard`・`face_down` | 選べるものの `pokemon`・`card`・`zone`・`bench_index`・`card_id`・`face_down` |
| 0.169.0（U7-5c） | `play_trainer` | `trainer` | 理由 `use_condition_not_evaluated` |
| 0.170.0（U7-5d） | `use_stadium` | `energy` | 候補の `stadium`（`card`・`card_id`・`owner`）、選べるものの `holder`（場のポケモンの形） |

- `implemented_kinds`・`gui_operable_kinds` に上の種類を加え、`turn_kinds_not_covered` を `use_power`・`check_face_up_deck` にする
- 段の role の表（`stage_roles`）に `play_trainer: ["trainer"]`、`use_stadium: ["energy"]`（エネルギーを選ばせる効果だけ。選ばせない効果は段がない）を加える
- 入力のない `use_stadium`（`input_disclosure: "no_input"`）は、`choices: []` で送る
- `unverified` の選べるもの（U7-5c の山札から引いて試す 5 つ）は `eligible: true` で送れる。使えるかは送るまで分からないと示す
- 受理のあとは `refetch_required` で候補を取り直し、決める人の `answer_decision` に答える（錯乱ジム・［ちえくらべ］は相手が決める）。新しい決定の種類の入力は既存の `answer_decision` の形
- 同じ形式の版（1）であることを、GUI がそのまま動く保証にはしません（GUI を動かしていない）

### 8.3 JSON の例（client_api の実際の応答から、保証の文などを除いて短くした）

エネルギーを選ばせる効果（ヤマブキシティジム）:

```json
{"contract": "kyuura-client-api", "format": 1, "type": "inputs", "game": "…", "revision": "…", "candidate": "c4"}
→ {"candidate": "c4", "kind": "use_stadium", "stages": [{"stage": 1, "input": "choose_option", "role": "energy", "meaning": "card", "count": {"min": 1, "max": 1},
     "order": "not_applicable", "options": [{"id": "o1", "card": 1, "card_id": "PMCG1-101",
       "holder": {"pokemon": 1, "card": 0, "zone": "active", "card_id": "PMCG6-043"}, "eligible": true, "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"]}]}]}
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c4", "choices": ["o1"]}
→ {"ok": true, "outcome": "accepted", "result": {"status": "in_progress", "next": [{"kind": "turn_action", "player": 0}], …}, "refetch_required": true}
```

選ばせるもののない効果と、受理のあとの決定（エネルギースタジアムの「おもて」）:

```json
候補: {"id": "c4", "kind": "use_stadium", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"], "choices_format": "[]",
       "stadium": {"card": 3, "card_id": "NIP1X-009", "owner": 0}, "input_disclosure": "no_input", "input_stages": []}
{"type": "submit", …, "candidate": "c4", "choices": []}
→ {"outcome": "accepted", "result": {"status": "awaiting_decision", "next": [{"kind": "answer_decision", "player": 0}], …}, "refetch_required": true}
取り直した候補の inputs: {"kind": "answer_decision", "stages": [{"stage": 1, "input": "choose_option", "decision_kind": "retrieve_energy", "meaning": "card", "count": {"min": 1, "max": 1},
       "decline": false, "options": [{"id": "o1", "card": 14, "card_id": "PMCG1-098", "processability": "may_stop_later"}, {"id": "o2", "card": 15, "card_id": "PMCG1-099", …}]}]}
```

- トレーナー（`play_trainer`）の宣言と、錯乱ジムで相手が答える流れ（`ACCEPT_REQUEST`。使えない相手の「使う」は相手にだけ `rejected`、「使わない」は `accepted`）は、[legal-actions-u7-5c](legal-actions-u7-5c.md) 8 章の例のとおりです
- 拒否と受理のあとの停止の区別: ホストの段の拒否は `outcome: "refused"`（`refusal.code`）、エンジンの拒否は `outcome: "rejected"`（状態は変わらない）。受理のあとの停止・決定待ちは `outcome: "accepted"` のあとの `status`・`next` で示します

## 9. 確かめたこと

限定の範囲です。全体のテスト・状態の監査・108 のバッチ・4,356 局・lockstep の全体・広いストレステストは流していません。

- **テスト**: 1 モジュールずつ別のプロセスで、並列にしないで流しました（2026-11-08。開始・終了・件数・終了コードを実行ごとに保存）。22 対象・528 件、すべて成功・終了コード 0・skip 0
  - 新しい `tests/test_legal_actions_u7_5d.py`: 25 件
    - コードの上の網羅（補助関数）: 登録した 24 の型すべての `activated`・`energy_choice` と `check_activation` の対応、常時の効果だけの 16 の型に候補がないこと、`check_use_stadium` とコマンドの処理の拒否の一致
    - 構築盤面: 代表のスタジアム、使う主体（相手が出したスタジアムを番のプレイヤーが使う）、回数、コインの両面、受理のあとの決定、キョウの忍者ジムの双子、取っ手、不正な入力、状態の不変、client_api
    - new_game からの合法な操作の列（固定の seed 1。3 つの規約集合）: 準備 → `play_trainer` でラッキースタジアムを出す → `use_stadium` → 番を終える。直接の列と同じ状態、完全な再現用記録の収集・U4 の再実行（`succeeded`）・閲覧用記録の構造。キョウの忍者ジムの v0.146 の列（seed 1・17）の双子
  - U7: `u7_5c` 32・`u7_5_design` 27・`u7_1` 42・`u7_2` 17・`u7_3` 29・`u7_4` 27・`u7_5ab` 27・`api_design` 13・`decision_audit` 15・`client_api` 9
  - スタジアムと T-F1・F-8: `test_stadiums_v0_57` 27・`test_remaining_stadiums_v0_74` 34・`test_ninja_gym_oracle_v0_146` 13・`test_stadium_reuse_special_energy_v0_58` 41・`test_chaos_gym_borrow_t_f1` 12
  - 記録・再実行・閲覧用記録・保存と復元: `replay_record_v0_153` 25・`replay_run_v0_154` 23・`view_record_v0_155` 24・`state_snapshot_v0_157` 37・`snapshot_replay_v0_158` 28
  - 版: `test_preset_decks_v0_20` の `StartGameTest.test_version` 1
- **生成物・データの検査**: `scripts/build_*.py --check` の 11 個と、`check_implementation_assumptions --check`・`check_normalization_revalidation --check`・`check_card_sources`・`check_research_links` は終了コード 0
  - 停止の台帳は作り直して、`engine.py`・`effects.py` の行番号だけが変わりました（836 行。ほかの項目の変化なし）
  - `check_implementation_assumptions --sites` の出力は基点 `13249d0` と同じ（56 行）
- **lint**（ruff 0.17.2）: 新しいファイル・`legal_actions.py`・U7 のテスト・U7-5 の生成器は指摘なし。`engine.py`・`effects.py`・`__init__.py`・`test_preset_decks_v0_20.py` の指摘の数は基点と同じ
- **配布と通常のインストール**: このあとの文書だけのコミットで記録します

## 10. 未確認・未対応

- `check_activation` が呼ぶ別のモジュールの関数（`persistent`・`conditions` など）の 2 段目より先は、名前と読む属性だけを見ました
- キョウの忍者ジムの保守的な NJ1 は、v0.146 のままです（緩めていない）
- U7-5c の山札から引いて試す 5 つ（PT-5e）の読む値は、別の監査の課題のままです（今回は依存しない）
- U7-5e（`UsePokemonPower`）・U7-5f（`CheckFaceUpDeckCard`）・U7-5g（R-1・R-2・coverage の閉じ方）は未実装です
