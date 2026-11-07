# U7-5c: 手札のトレーナー（PlayTrainer）の候補・入力・検査・送信（v0.169）

U7-5 の計画（[legal-actions-u7-5-design](legal-actions-u7-5-design.md)・[legal-actions-u7-5-implementation-plan](legal-actions-u7-5-implementation-plan.md)）の 3 番目の単位です。T-F1・F-8 の情報漏れの修正（[chaos-gym-borrow-t-f1](chaos-gym-borrow-t-f1.md)。v0.168）のあとに、本人の手札から既存の `PlayTrainer` を公開の API（合法手 API・client_api）で送れるようにしました。

- 基点: `8de0e21`（T-F1 の最終コミット。main は `0c00b56` のままで、T-F1 はまだ取り込まれていない）。作業ブランチ `claude/u7-5c-trainer`
- 実装していないもの: `UsePokemonPower`・`UseStadium`・`CheckFaceUpDeckCard`・カツラの 2 枚目（`AttachEnergy.energy2`。R-1）。U7-5d 以降は未実装のまま
- GUI・renderer・kyuura・カードデータ・固定デッキ・3 つの規約集合・過去の参照データは変えていません

## 1. 対応の範囲

| 候補の種類 | コマンド | 宣言の入力 | 受理のあと |
|---|---|---|---|
| `play_trainer`（新しい種類） | `PlayTrainer(player, card)` | `card`（手札のトレーナーカード 1 枚）。`player` は主体（取っ手が決める） | 既存の決定（`answer_decision` の候補で答える） |

- コマンドの項目は `player`・`card` の 2 つだけ（`dataclasses.fields` で確かめた）。設計（U7-5 の設計 4 章）のとおり、宣言の入力は `card` だけです
- `PlayTrainer` として実行される次のものを、同じ種類で扱います
  - 通常のトレーナー（マサキ・きずぐすり・エネルギー転送・パソコン通信など）
  - どうぐ（プラスパワー・ディフェンダー）
  - 手札から場に出すスタジアム（錯乱ジムなど）
  - ポケモンとして場に出すトレーナー（なにかの化石・ピッピ人形）
  - 使うと番が終わるカード（ロケット団員の「うら」など）
- 対象・枚数・費用・山札の検索・任意の選択は、すべて受理のあとの既存の決定です。宣言の前に移していません
  - 錯乱ジムのコイン → 相手の `ACCEPT_REQUEST`、相手の［ちえくらべ］（`REACTION_POWER`）、リムーブ禁止ジムの追加の条件（`DISCARD_FROM_HAND`）、効果の決定、サイキックコントロールの使うカード（`USE_DISCARD_TRAINER`）と、その内側の使用
- 場のスタジアムの効果（`UseStadium`）・特殊能力（`UsePokemonPower`）は混ぜていません（`use_stadium`・`use_power` は対応しない種類のまま）

## 2. 候補の形

- 1 段の `choose_option`（`role: "trainer"`・`meaning: "card"`・`count` 1〜1・`order: "not_applicable"`）。選べるものは本人の手札の並びのトレーナーカード（`card`・`card_id`。U7-3 の `_card_option` と同じ形）
- 候補の並びは `MAIN_KINDS` の順（`use_attack` のあと、場のポケモン 1 匹を指す操作の前）。`implemented_kinds` では最後に加えました
- `choices_format` は `[手札のカードの番号]`（選ぶものの番号 `o1` など）
- ゲーム上できないカード（エンジンの確かめが `IllegalActionError`）は選べるものに出しません。選べるものがなければ候補を作りません（トレーナーの使用の禁止・手札にトレーナーがない）
- 未裁定・未対応（`UnsupportedError`）は選べるものに出し、実行できない区分にします（`eligible: false`。送る前に `CANDIDATE_NOT_EXECUTABLE`）
  - 登録のないトレーナー: `not_implemented`
  - MG1（場の錯乱ジムと相手の［ちえくらべ］）・カードごとの未裁定（傷のないきずぐすり・控えのいないポケモンいれかえなど）: `unresolved_ruling`
  - 技術的制限のコード: `technical_limit`（区分は診断のコード表。補助の確かめで表示を確かめた）

## 3. 共通にした確かめと、残した実行時の先読み

`engine._play_trainer` の手札から出す前の部分を `engine.check_play_trainer(state, cmd, *, use_condition=True)` に移しました。順番・コード・理由の文・副作用（なし）は同じで、`_play_trainer` はこれを呼んでから手札から出します。

| 分類 | 確かめ | 候補の作成で |
|---|---|---|
| A（公開・本人の知識） | 番・段階（`require_turn`）、本人の手札、トレーナーカードであること、トレーナーの使用の禁止（場の力・期限のある禁止）、登録表、リムーブ禁止ジムの追加の条件（本人の手札の枚数）、MG1（相手の場の［ちえくらべ］と場の錯乱ジム） | 呼ぶ |
| A・A-own（カードごと） | 使うための条件（`TrainerEffect.check_playable`）のうち、下の 5 つを除くもの | 呼ぶ |
| B（入力が完成してから） | なし（入力は card だけで、候補の作成で全部確かめる） | — |
| C（受理のあとの決定・コイン・検索） | 錯乱ジムのコインと `_chaos_tails`、［ちえくらべ］の答え、効果の決定 | 呼ばない（受理のあとの決定として答える） |
| D（実際の状態を試す先読み） | `_trainer_reaction_decline_check`（［ちえくらべ］を使わない続き）、`_trainer_dead_end`（効果の途中の決定の答えの続き）、`_apply_once` のコマンドの終わりの確かめ | 呼ばない。エンジンの実行ではそのまま残す |
| E（読む情報が未確認） | 使うための条件のうち、実際の山札から引いて試す 5 つ（`PLAYABLE_NOT_EVALUATED`） | 呼ばない（`unverified`） |

- `use_condition=False` は、カードごとの使うための条件だけを呼ばない指定です。エンジンの処理はいつも真で呼びます
- 候補の作成は `apply_command`・効果の試行・先読みを呼びません。D の確かめがあるので、トレーナーの候補は `supported` にしません（`may_stop_later`）

## 4. カードごとの使うための条件（A-own の 6 と E の 11）

U7-5 の設計の静的な走査（`scan.check_playable`。effects.py の 77 の実装）を、今のコードで照らしました。走査そのものは `scripts/build_legal_actions_u7_5_design.py --check` が今のコードと比べます。

### 4.1 持ち主の知識の関数を呼ぶ 6 の実装（A-own）

`BenchNameGroupFromDeckTrainer`・`CoinsSearchBasicEnergyPerHeads`・`DiscardDeckTopThenReturnTypeEnergy`・`LookTopTakePokemonThenShuffle`・`ReturnHandEnergyThenCoinSearchBasicEnergy`・`SearchDeckTrainer`

- 入力は使うプレイヤーと状態、出力は拒否（`IllegalActionError`・`UnsupportedError`）だけです。読むのは、山札とサイド（と持ち主に見えない置いておくカード）を合わせた持ち主の知識の下限（`deck_target_lower_bound`・`deck_lower_bound_where`・`searchable_deck_cards`。v0.137〜v0.151 の修正）と、山札の枚数（公開）です
- 候補の作成で呼びます。山札とサイドの配分だけを変えた双子（エネルギー転送・パソコン通信）で、本人の候補・入力・入力の検査の応答と、相手・観戦者の観測・ログが一致することを確かめました（`tests/test_legal_actions_u7_5c.py` の `UseConditionTest.test_owner_knowledge_twins`）
- 実際の配分を読む判定には戻していません

### 4.2 状態の複製の上で試す 11 の実装（E）

| 群 | 実装 | 試すもの | 候補の作成で |
|---|---|---|---|
| 場だけを試す（`PLAYABLE_BOARD_TRIALS`） | `SwitchWithBench`・`SwitchOpponentWithBench`・`CoinStatusOnOpponentActiveTrainer`・`ConditionOwnActiveTrainer`・`CoinHealBothElseSleepBoth`・`CoinHealAndCureOwnActive` | 入れ替え・特殊状態・回復を複製の上でして、`state_stop_after`・`switch_max_hp_drop_check`（決められない姿・MH1・SC2） | 呼ぶ |
| 実際の山札から引いて試す（`PLAYABLE_NOT_EVALUATED`） | `BlainesQuiz`・`BlainesHeightQuiz`・`SetAsideGuessKindQuiz`・`GuessOpponentPrizeKind`・`SwapPleaseTrainer` | 複製の上で山札から引いて（`_draw_up_to`）、おもての山札の止め方を比べる | 呼ばない（`unverified`） |

- 場だけを試す 6 つは、effects.py の中の呼び出しの閉包と、呼ぶ別のモジュールの関数（`conditions`・`persistent`・`markers`・`stadiums`・`state` の 13 の関数）の 1 段目までをたどりました
  - 読むのは、場のポケモン・カードの定義・番・場の効果の記録（色・エネルギーの役割・固定した変身の姿）だけでした
  - 山札・サイド・手札・置いておくカード・うらのカードの集合は読みません
  - うらのカードの定義を読むと、本当のカードによらず FD1（`HiddenPropertyRead`）で止まります
  - 複製の上の試行であることを、安全の根拠にはしていません
- 実際の山札から引いて試す 5 つは、読む値をたどっていません
  - v0.135 の記録（結果はそれぞれの山札の枚数とおもての枚数だけで決まる）はありますが、今回は確かめ直していないので、候補の作成・inputs・check では呼びません
  - カードの選択の表示は本人の手札だけで決まるので、入力は返します（`input_disclosure: "confirmed"`）
  - 選べるものの数・並びは、条件の結果によりません。使えるかは処理可能性 `unverified`（理由 `use_condition_not_evaluated`）で示し、送ればエンジンが決めます
  - エンジンの拒否は送った人にだけ返ります（CORR-1 と同じ考え方: 未確認の判定の結果を、選べるもの・件数・理由に出さない）
- 条件を定義した型（継承をたどる）が effects.py にないものも、候補の作成では呼びません（`unverified`。補助の確かめで確かめた）
- `PLAYABLE_NOT_EVALUATED` と `PLAYABLE_BOARD_TRIALS` を合わせたものが設計の走査の 11 と一致することを、テストが確かめます。新しい試行の型が加わると、分類するまでテストが通りません

## 5. 情報境界・処理可能性・coverage

- 候補は本人の手札と公開の情報だけで作ります。相手・観戦者には候補を送りません（番でない主体の候補は `waiting_for_player`・候補なし。観戦者には候補の入口がない）
- 双子で確かめたこと（本人の候補・件数・並び・制約・理由・不正な入力への応答・相手と観戦者の観測とログ）
  - 相手の手札の中身と山札の並び
  - 本人の山札の並び
  - 本人の山札とサイドの配分（A-own）
- 処理可能性の区分は既存の 6 つのままです。トレーナーの候補は `supported` にしません
  - 使うための条件を呼んだカードは `may_stop_later`（理由 `preflight_not_evaluated`・`continuation_not_evaluated`）
  - 呼ばないカードは `unverified`（理由に `use_condition_not_evaluated` を加える）
- coverage: 番の操作の `not_covered_kinds` から `play_trainer` が外れ、`use_power`・`use_stadium`・`check_face_up_deck` が残ります。`completeness` は `partial` のままです
  - 残る経路: R-1（カツラの 2 枚目の「炎」エネルギー。U7-3 の attach_energy が使わない）、R-2（自分のうらのバトル場のポケモンの宣言といっしょに選ぶもの。U7-4 は示さない）
  - coverage の項目の意味・並び（`scope_kinds` は `MAIN_KINDS` の順）は変えていません

## 6. 既存のエンジンとの一致と、意図した差

- U7 経由・client_api 経由・直接のコマンドで、受理・拒否の結果、状態・乱数・ログ、送り手への診断が一致することを確かめました
  - 通常のトレーナー、対象の決定、費用と検索の決定、どうぐ、スタジアム、化石・人形、番を終えるカード、錯乱ジム、［ちえくらべ］、サイキックコントロール
- エンジンの動作は変えていません（`_play_trainer` の前半を関数にしただけ）
- 意図した差: 既存の U7 のテスト（U7-1・U7-3・U7-4・U7-5a＋b）の coverage の期待から `play_trainer` を外しました（対応した種類になったため）。U7-5 の設計のテストの、壊して確かめる対象の単位を U7-5c から U7-5d に移しました
- 錯乱ジムの T-F1 の扱い（使えない相手にも `ACCEPT_REQUEST` を出し、「使う」の答えを拒否する）と、F-8（サイキックコントロールの選べるものは公開の情報だけで作る）を、U7 の答えでも確かめました
- F-9（公開の情報だけで使えないと分かる場合にも決定を出す今の扱い）は変えていません
- CH1・MG1・TL1 の止め方と、費用・公開・カードの移動・番の終わりの順は変えていません

## 7. client_api と取っ手

既存の `candidates`・`inputs`・`check`・`submit` をそのまま使います。主体は入口で固定します。

- 受理: その対戦の取っ手をすべて失効させる
- 拒否（ホストの段の `refused`・エンジンの `rejected`）: ほかの主体の取っ手を失効させない。拒否の存在を相手・観戦者へ知らせない
- 古い取っ手（`CANDIDATES_STALE`）・別の主体（`CANDIDATES_WRONG_ACTOR`）・別の対戦（`CANDIDATES_WRONG_GAME`）を拒否する
- 通常の応答に、検証者の情報・生の例外の文・完全な状態を出さない（`FORBIDDEN_KEYS` で確かめた）
- 区別するもの
  - ホストの段の拒否（`outcome: "refused"`。`refusal.code` が `CANDIDATE_INPUT_INVALID`・`CANDIDATE_NOT_EXECUTABLE` など）
  - エンジンの拒否（`outcome: "rejected"`。状態は変わらない）
  - 受理のあとの停止（`outcome: "accepted"` のあと、`status`・`next` で決定待ち・停止を示す）

## 8. GUI への引き継ぎ（GUI リポジトリは変更していない）

- **契約識別と形式版**: `kyuura-client-api`・形式 1（変えていない）。合法手 API の形式 `kyuura_legal_actions_format` 1（変えていない）
- **新しいもの**
  - 候補の種類 `play_trainer`
  - 段の `role: "trainer"`
  - 理由 `use_condition_not_evaluated`
  - 項目の追加はない（選べるものは U7-3 の手札のカードと同じ `card`・`card_id`・`eligible`・`processability`・`reasons`）
- **固定して導入確認した完全コミット**: このコミットのあとの文書だけのコミットで、10 章に記録します

### 8.1 card の選択から check・submit まで（錯乱ジムを場に出す例。client_api の実際の応答から短くした）

```json
{"contract": "kyuura-client-api", "format": 1, "type": "inputs", "game": "…", "revision": "…", "candidate": "c5"}
→ {"ok": true, "response": {"candidate": "c5", "kind": "play_trainer", "stages": [{"stage": 1, "input": "choose_option", "role": "trainer", "meaning": "card",
     "count": {"min": 1, "max": 1}, "order": "not_applicable", "options": [
       {"id": "o1", "card": 3, "card_id": "PMCG5-087", "eligible": true, "processability": "may_stop_later", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]},
       {"id": "o2", "card": 4, "card_id": "PMCG1-093", "eligible": true, "processability": "may_stop_later", "reasons": ["continuation_not_evaluated", "preflight_not_evaluated"]}]}]}}
{"contract": "kyuura-client-api", "format": 1, "type": "check", "game": "…", "revision": "…", "candidate": "c5", "choices": ["o1"]}
→ {"ok": true, "response": {"valid": true, "refusal": null}}
{"contract": "kyuura-client-api", "format": 1, "type": "submit", "game": "…", "revision": "…", "candidate": "c5", "choices": ["o1"]}
→ {"ok": true, "outcome": "accepted", "result": {"status": "in_progress", "next": [{"kind": "turn_action", "player": 0}], …}, "refetch_required": true}
```

### 8.2 宣言のあとの決定と、相手が答える例（錯乱ジムの「うら」）

- ポケモン交換おじさんを送ると、`outcome: "accepted"`・`status: "awaiting_decision"`・`next: [{"kind": "answer_decision", "player": 1}]`
- 使ったプレイヤーの候補は `waiting_for_player`
- 相手の候補は `answer_decision`（`decision_kind: "accept_request"`・`count` 0〜1・`decline: true`・選べるもの `o1`）
- 相手の手札にポケモンがなく使えないときに `["o1"]`（使う）を送ると、`outcome: "rejected"`（相手にだけ返る。診断は相手の手札の理由。状態は変わらない）
- `[]`（使わない）は `accepted`。カードは持ち主のトラッシュに行き、使ったプレイヤーの番に戻る

### 8.3 GUI の型・検証・表示に必要な変更（GUI を動かしていないので、対応を保証しない）

- 候補の種類の型に `play_trainer`、段の role に `trainer`、理由のコードに `use_condition_not_evaluated` を加える
- `unverified` の選べるものは `eligible: true` で送れる。使えるかは送るまで分からないことを示す
- 受理のあとは `refetch_required` で候補を取り直し、決める人の `answer_decision` に答える（決めるのが相手のことがある。錯乱ジム・［ちえくらべ］）
- 受理のあとの決定の種類は多い（検索・見たカード。U7-1 の `DECK_REVEALING_KINDS` の契約の例外のまま）。入力を返さない決定（`input_disclosure: "unconfirmed"`）は、今までどおり未対応として示す

## 9. 確かめたこと

限定の範囲です。全体のテスト・状態の監査・108 のバッチ・4,356 局・lockstep の全体・広いストレステストは流していません。

- **テスト**: 1 モジュールずつ別のプロセスで、並列にしないで流しました（2026-11-08。開始・終了・件数・終了コードを実行ごとに保存）
  - 新しい `tests/test_legal_actions_u7_5c.py`: 32 件成功
  - 既存のテスト 21 対象: `test_instant_trainers_v0_55` を除く 20 対象は、すべて成功・終了コード 0・skip 0
    - U7: `u7_5_design` 27・`u7_1` 42・`u7_2` 17・`u7_3` 29・`u7_4` 27・`u7_5ab` 27・`api_design` 13・`decision_audit` 15・`client_api` 9
    - T-F1 とトレーナー: `test_chaos_gym_borrow_t_f1` 12・`test_stadiums_v0_57` 27・`test_stadium_reuse_special_energy_v0_58` 41・`test_slowking_mind_games_v0_132` 31・`test_trainers` 45
    - 記録・再実行・閲覧用記録・保存と復元: `replay_record_v0_153` 25・`replay_run_v0_154` 23・`view_record_v0_155` 24・`state_snapshot_v0_157` 37・`snapshot_replay_v0_158` 28
    - 版: `test_preset_decks_v0_20` の `StartGameTest.test_version` 1
  - `test_instant_trainers_v0_55`（51 件）: 既定の文字コードではエラー 2（テストが `kyuura_cards.json`・`card_sources.json` を文字コードを指定せずに読み、Windows の cp932 で失敗する。今回の変更と関係しない既存の環境の依存）。`PYTHONUTF8=1` でもう一度流して 51 件すべて成功
- **生成物・データの検査**: `scripts/build_*.py --check` の 11 個と、`check_implementation_assumptions --check`・`check_normalization_revalidation --check`・`check_card_sources`・`check_research_links` は終了コード 0
  - 停止の台帳は作り直して、`engine.py` の行番号だけが変わりました（18 行。ほかの項目の変化なし）
  - `check_implementation_assumptions --sites` の出力は基点 `8de0e21` と同じ（56 行）
- **lint**（ruff 0.17.2）: 新しいファイル・`legal_actions.py`・U7 のテスト・U7-5 の生成器は指摘なし。`engine.py`・`__init__.py`・`test_preset_decks_v0_20.py` の指摘の数は基点と同じ
- **配布と通常のインストール**: 10 章のあとの文書だけのコミットで記録します

## 10. 未確認・未対応

- PT-5e の 5 つ（実際の山札から引いて試す）の読む値は、たどっていません（`unverified`）
- 場だけを試す 6 つと A 群の閉包のうち、別のモジュールの関数の 2 段目より先は、名前と読む属性だけを見ました
- D の先読み（`_trainer_dead_end` など）による受理の前の拒否は、候補で予告しません（`may_stop_later`）
- U7-5d（`UseStadium`）・U7-5e（`UsePokemonPower`）・U7-5f（`CheckFaceUpDeckCard`）・U7-5g（R-1・R-2・coverage の閉じ方）は未実装です
