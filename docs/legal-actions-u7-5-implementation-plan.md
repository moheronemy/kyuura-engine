# U7-5: 実装計画（承認前）

[legal-actions-u7-5-design](legal-actions-u7-5-design.md) の仕様を、安全に実装できる単位に分けた計画です。表は `scripts/build_legal_actions_u7_5_design.py` が作ります。どの単位も `planned` で、この計画では実装していません。情報源が未確認（E）の経路は、対応済みに数えません。

## 1. 単位

<!-- generated:rest-units begin -->
| 単位 | 名前 | コマンド | 依存 | 変更範囲 | 完了の基準 | GUI への引き継ぎ | 残る事項 |
|---|---|---|---|---|---|---|---|
| `U7-5a`（最初） | 場のポケモン 1 匹を指す操作（RemoveDisguise・DiscardFromPlay） | `RemoveDisguise`<br>`DiscardFromPlay` | U7-4 | engine.py: 2 つの処理の受理の前の部分を、同じ順番・同じコード・同じ文のまま check_remove_disguise・check_discard_from_play にする（U7-3 の check_* と同じ）<br>legal_actions.py: 2 種類の候補（1 段・choose_option・場のポケモンの番号）。うらのカードは DiscardFromPlay の候補に出さない（F-2 の FD1 に当てない） | 2 種類が evaluated になり、MH1・TK1 に当たる候補は may_stop_later、DiscardFromPlay は U7-3 と同じ条件でだけ supported。直接のコマンドとの一致・双子（うらのカードの本当のカード）が通る | 1 段の choose_option（場のポケモンの番号）。決定への接続は promote_active の候補（空いたバトル場） | なし |
| `U7-5b` | うらのカード（RevealFaceDown） | `RevealFaceDown` | U7-5a | engine.py: _reveal_face_down の受理の前の部分を check_reveal_face_down にする<br>legal_actions.py: 1 段の候補。候補に結果（残るか）を書くかは D-U75-REVEAL-OUTCOME | 相手・観戦者の応答が、本人のうらのカードの本当のカードで変わらない双子（たね・たねでない）が通る。おもてにしたあとのログが観測の規則どおり | 1 段。おもてにしたあとの公開のログ（secret_plan_revealed・secret_plan_discarded）の表示 | なし |
| `U7-5c` | 手札のトレーナー（PlayTrainer） | `PlayTrainer` | U7-5a | engine.py: _play_trainer の手札から出す前の部分を check_play_trainer にする<br>legal_actions.py: 1 段の候補。E の 11 の実装は unverified、登録なしは not_implemented、停止は診断のコード表の分類 | A-own の 6 の実装で双子が通る。錯乱ジムの「うら」・［ちえくらべ］・サイキックコントロールは受理のあとの決定として new_game からの列でつながる。E の 11 の実装は unverified のまま数える | 1 段。受理のあとの決定の種類が多い（検索・見たカード。U7-1 の DECK_REVEALING_KINDS の契約の例外） | PT-5e の 11 の実装の読む値をたどる<br>F-1 の扱い（D-U75-CHAOS） |
| `U7-5d` | 場のスタジアム（UseStadium） | `UseStadium` | U7-5a | engine.py: _use_stadium の check_activation までを check_use_stadium にする<br>legal_actions.py: 選ばせるもののない候補と、energy の 1 段の候補 | 持ち主でないプレイヤーの使用・同じ番の 2 回目（STADIUM_ALREADY_USED・LK1）・キョウの忍者ジムの双子が通る | 選ばせるもののない候補と 1 段の候補 | なし |
| `U7-5e` | 宣言する特殊能力（UsePokemonPower） | `UsePokemonPower` | U7-5b<br>U7-5d | effects.py: 型ごとの選ばせるものの宣言（D-U75-INPUT-DECL。挙動は変えない）<br>engine.py: _use_pokemon_power の宣言の前の部分を check_use_pokemon_power にする（_reveal_for_action の扱いは D-U75-POWER-FACE-DOWN）<br>legal_actions.py: 特殊能力 → 選ばせるもの（2〜3 段） | 形ごとに 1 つ以上の代表で、宣言の入力・受理のあとの決定・回数の制限が通る。相手のうらのカードを指す選択は unverified。E の 7 の実装は unverified | 2〜3 段（depends_on_stage = 2 の提案） | UP-5e の 7 の実装の読む値をたどる<br>D-U75-INPUT-DECL<br>D-U75-POWER-FACE-DOWN |
| `U7-5f` | おもての山札の確かめ（CheckFaceUpDeckCard） | `CheckFaceUpDeckCard` | U7-5a | legal_actions.py: 相手の山札のおもての 2 枚目より下の位置を unresolved_ruling で示す（送れない） | 候補の位置が、おもての枚数（公開）だけで決まる双子（おもてのカードの中身を変える）が通る | 表示だけ（送信のボタンを出さない） | なし |
| `U7-5g` | 残りの経路と coverage の閉じ方 | なし | U7-5c<br>U7-5e<br>U7-5f | R-1・R-2 の扱い（D-U75-ENERGY2）<br>段階・主体ごとの coverage の表し方（C-6） | C-1〜C-6 を満たすかを、単位ごとの結果から判断できる | coverage の表示 | D-U7-COMPLETENESS |
<!-- generated:rest-units end -->

## 2. 推奨順序と根拠

| 順 | 単位 | 共通の処理 | 情報境界 | 宣言の入力 | GUI で対戦できる範囲への効果 | 既存のテスト・代表の盤面 | 未裁定・技術的な制限への依存 |
|---|---|---|---|---|---|---|---|
| 1 | U7-5a | 受理の前の確かめが 3〜4 個 | 公開の値だけ | 場のポケモン 1 つ | 小（化石・人形・「ばける」の盤面） | v0.47・v0.49・v0.93 | MH1・TK1（処理のあと） |
| 2 | U7-5b | 同じ形 | 本人のうらのカード（双子が要る） | 場のポケモン 1 つ | 小（マチスの秘策） | v0.67 | なし |
| 3 | U7-5c | 手札から出す前の部分（8 個の確かめ＋77 の実装） | A・A-own・E（11） | 手札のカード 1 つ | 大（固定デッキのトレーナー） | v0.55・v0.57・v0.132 ほか | MG1・カードごとの未裁定。F-1 |
| 4 | U7-5d | `check_activation` まで | A・A-own（忍者ジム） | なし・energy | 中 | v0.57・v0.74・v0.146 | STB1・LK1・FG1・NJ1・GG1 |
| 5 | U7-5e | 宣言の前の部分＋70 の実装 | A・A-own・B・D（相手のうらのカード）・E（7） | 9 通りの形（2〜3 段） | 大 | v0.5・v0.6・v0.42 ほか | DV3・TF1・SV3。D-U75-INPUT-DECL |
| 6 | U7-5f | 要らない | 公開の枚数 | 位置 | なし（表示だけ） | v0.126 | FU2 |
| 7 | U7-5g | なし | なし | R-1（カツラ） | 小 | v0.59 | なし |

GUI の対戦への効果だけなら U7-5c（トレーナー）が先ですが、a・b で「処理の前半を関数にする」「本人のうらのカードの双子」の型を小さく固めてから c・e に進みます。c は宣言の入力が 1 つなので、e より先にします。

## 3. 最初の単位: U7-5a（RemoveDisguise・DiscardFromPlay）

コード上の根拠:

<!-- generated:rest-first begin -->
- 2 つの処理の受理の前の確かめは 3〜4 個で、どれも公開の値（番・自分の場・disguise・場での役割・leave_lock。RD-1・DF-1・DF-2）
- 宣言の入力は pokemon 1 つだけ（登録が決める選ばせるものがない）。コイン・宣言の前の先読み・カードごとの確かめ（77・70・9 の実装）を通らない
- 相手のうらのカードを指定しない（designate_face_down を呼ばない）ので、_identity_independent の試行が起こらない
- 処理のあとの確かめで止まるのは RemoveDisguise の MH1・TK1 だけ。DiscardFromPlay は決定を出さず、空いたバトル場だけ
- 代表の盤面: tests/test_virtual_attacks_transformation_v0_49.py（タケシのキュウコンの「ばける」）、tests/test_fossil_hidden_info_v0_47.py（なにかの化石・ピッピ人形）、tests/test_active_leave_locks_v0_93.py（バトル場をはなれられない）
<!-- generated:rest-first end -->

具体化:

- **エンジン**（挙動を変えない関数化）
  - `engine._remove_disguise` の受理の前の部分を `check_remove_disguise(state, cmd) -> (player_state, pokemon)` にします。`require_turn`・場の番号・`POKEMON_NOT_YOURS`・`POKEMON_NOT_IN_PLAY`・`NOT_DISGUISED` を、同じ順番・同じコード・同じ文のまま移します
  - `engine._discard_from_play` も同じく `check_discard_from_play` にします（`NOT_DISCARDABLE`・`LEAVE_ACTIVE_PREVENTED` まで）
  - 停止の台帳（`docs/stop-policy-classification.json`）は行番号だけが変わる見込みです。作り直して、ほかの差がないことを確かめます
- **候補**（`legal_actions.py`）
  - 種類 `remove_disguise`・`discard_from_play`。1 段（`choose_option`・`meaning: pokemon`・`count 1..1`・`order: not_applicable`）
  - 選べるものは自分の場のポケモンで、関数の確かめで ILLEGAL のものは出しません。`DiscardFromPlay` は本人のうらのカードを選べるものに出しません（`state.is_face_down` は公開。F-2 の FD1 に当てない）
  - `RemoveDisguise` は `may_stop_later`（理由: 処理のあとの MH1・TK1 を評価していない）。`DiscardFromPlay` は U7-3 の `supported` の条件（受理のあとの停止のもとが場にないことを公開の情報で確かめた）を使い、ほかは `may_stop_later`
- **入力の検査と送信**: `check` で関数をもう一度呼び、ILLEGAL は `CANDIDATE_INPUT_INVALID`。送信は既存のアダプタ（最終の判定は `apply_command`）
- **JSON の例**（U7-4 の 7.1 節と同じ形の案。値は例。まだ実装していない）:

`candidates` の応答の 1 件:

```json
{"id": "c7", "kind": "discard_from_play", "processability": "may_stop_later", "reasons": ["continuation_not_evaluated"],
 "guarantees": {"preconditions": "…check_discard_from_play…", "acceptance": "…", "after_acceptance": "…"},
 "choices_format": "[すてる場のポケモンの番号]", "input_disclosure": "confirmed", "input_stages": [{"stage": 1, "input": "choose_option"}]}
```

`inputs` の 1 段目（選べるものは `_pokemon_option` の形。本人のうらのカードは出さない）:

```json
{"stage": 1, "input": "choose_option", "role": "pokemon", "meaning": "pokemon", "count": {"min": 1, "max": 1}, "order": "not_applicable",
 "options": [{"id": "o1", "pokemon": 3, "card": 12, "zone": "bench", "bench_index": 0, "card_id": "PMCG3-046", "eligible": true, "processability": "may_stop_later",
              "reasons": ["continuation_not_evaluated"]}]}
```

- **完了の基準**: 1 章の表の U7-5a の行。加えて、U7-1〜U7-4 のテストの期待（`not_covered_kinds`・候補の種類の並び）の変更は、2 種類が加わったことだけです
- **GUI への引き継ぎ**: 1 段の `choose_option`。バトル場が空いたあとは `promote_active` の候補（U7-1）で答えます。GUI の契約の表（`turn_kinds_not_covered`）は、エンジンを更新すると食い違うので、GUI 側で直してからテストを通します

## 4. 検証の割り当て

構築盤面（`board`）・補助関数（`helper`）・new_game からの合法な操作列（`sequence`）を区別します。どの単位にも、構築盤面と new_game からの列の両方を置きます。

<!-- generated:rest-verify begin -->
| 確かめ | 意味 |
|---|---|
| `V-NORMAL` | 正常・拒否・受理のあとの停止（拒否と受理のあとの停止を結果で区別する） |
| `V-DECL` | 宣言の前の入力と、宣言のあとの決定（決定を宣言の前に移していない） |
| `V-NONTURN` | 番でない主体の操作（候補が空・送っても拒否・相手に拒否を知らせない） |
| `V-LIMIT` | 回数の制限（この番に使った・同じ番の再使用） |
| `V-TWIN` | 非公開のカードと秘密の配分を変えた双子（候補・件数・並び・理由・不正な入力への応答が一致） |
| `V-NOSIDE` | 候補・inputs・check で状態・乱数・ログが変わらない |
| `V-BADQUERY` | 不正な問い合わせ（知らない番号・型の違う値・重なり）の安全性 |
| `V-PARITY` | U7・client_api・直接のコマンドの結果の一致 |
| `V-HANDLE` | 取っ手の契約（受理で失効・拒否で他の主体の取っ手を失効させない・古い取っ手・別の主体・別の対戦） |
| `V-CONV` | 3 つの規約集合（CS-KYUURA-CURRENT・CS-KYUURA-PLAY-S2A・CS-KYUURA-PLAY-PO） |
| `V-INSTALL` | Git の URL からの通常のインストールと client_api のスモークテスト |
| `V-REGRESS` | 既存の U1〜U7 の回帰（U7-1〜U7-4・client_api・仕様の生成器の検査） |
| `V-JSON` | GUI が必要とする JSON の例（候補・入力・送信・決定への接続・停止と拒否） |

| 単位 | V-NORMAL | V-DECL | V-NONTURN | V-LIMIT | V-TWIN | V-NOSIDE | V-BADQUERY | V-PARITY | V-HANDLE | V-CONV | V-INSTALL | V-REGRESS | V-JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `U7-5a` | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5b` | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5c` | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5d` | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5e` | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5f` | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
| `U7-5g` | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） |  |  | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |

テストの種類: `board` = 構築盤面（build_test_state）・`helper` = 補助関数だけの確かめ（候補の作成を直接呼ぶ）・`sequence` = new_game からの合法な操作列
<!-- generated:rest-verify end -->

各単位の実装の検証予算は U7-4 と同じ限定検証です。新しいテスト・U7・client_api・直接関係する既存テスト・仕様と生成物の検査・配布の確かめとクリーンな環境のスモークテスト・変更したファイルの lint を流します。全体テスト・状態監査・全 108 バッチ・4,356 局・lockstep・広い範囲のストレステストは流しません。

## 5. 制約

- 採用の前に、エンジンの動作・候補の作成・入力の処理を変えません
- 識別の方式と互換性の判定・続行規約・3 つの規約集合の ID・版・内容・照合値を変えません
- kyuura・カードデータ・固定デッキ・過去の参照データ・GUI・renderer を変えません

## 6. この計画を作ったときの確かめ

- `python scripts/build_legal_actions_u7_5_design.py --check`（仕様の整合・コードとの対応）
- `tests/test_legal_actions_u7_5_design.py`（検査が通ること・壊した仕様を検査が見つけること）
- 関係する生成物の検査（U7 の仕様案の生成器・実装上の判断の一覧・停止の台帳）と、変更したスクリプト・テストの lint
- 結果の数は最終の報告に書きます（この文書に件数を固定しません）
