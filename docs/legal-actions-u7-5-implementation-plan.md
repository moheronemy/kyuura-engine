# U7-5: 実装計画（ADOPT-U7-5AB。U7-5a・U7-5b は v0.167 で実装）

[legal-actions-u7-5-design](legal-actions-u7-5-design.md) の仕様を、安全に実装できる単位に分けた計画です。表は `scripts/build_legal_actions_u7_5_design.py` が作ります。U7-5a・U7-5b は v0.167 で実装しました（[legal-actions-u7-5ab](legal-actions-u7-5ab.md)）。ほかの単位は `planned` です。情報源が未確認（E）の経路は、対応済みに数えません。

<!-- generated:rest-record begin -->
- `ADOPT-U7-5AB`（2026-11-08・利用者）: U7-5 の進め方と、U7-5a＋U7-5b の実装
  - 進め方:
    1. U7-5a＋U7-5b を 1 つの作業で実装
    2. 錯乱ジムの情報漏れ F-1 を別の作業 T-F1 で直す（両モード共通の不具合。トレーナーの前）
    3. U7-5c → U7-5d → U7-5e → U7-5f → U7-5g
  - 採用した判断:
    - `D-U75-ORDER`: 上の順（a＋b をまとめる。F-1 を c の前に直す）
    - `D-U75-FIRST`: 最初の実装は U7-5a＋U7-5b（RemoveDisguise・DiscardFromPlay・RevealFaceDown）
    - `D-U75-CHAINED`: 3 段の入力を認める。前の段を変えたら、それに依存する後の段をすべて無効にする（U7-5e で実装）
    - `D-U75-INPUT-DECL`: 型ごとの宣言の入力の記述（メタデータ）を設け、コマンドの作成・確かめとの対応をテストする（U7-5e で実装）
    - `D-U75-POWER-FACE-DOWN`: 相手のうらのカードは公開された位置・識別だけで扱い、隠れた定義を候補の作成に使わない（U7-5e で実装）
    - `D-U75-REVEAL-OUTCOME`: RevealFaceDown では、おもてにしたあとに場に残るかを候補で予告しない（U7-5b で実装）
    - `D-U75-FACE-UP`: CheckFaceUpDeckCard は FU2 による未対応として表示し、送れない（U7-5f で実装）
    - `D-U75-CHAOS`: F-1 は両モード共通の不具合として別の作業 T-F1 で直す（トレーナーの前）。U7-5a・b では裁定・動作を変えない
    - `D-U75-ENERGY2`: カツラの 2 枚目（AttachEnergy.energy2）は U7-5g に含める
    - `D-U75-TRAINER`: U7-5c（2026-11-08 の依頼）: 手札の PlayTrainer だけを扱い、UsePokemonPower・UseStadium・CheckFaceUpDeckCard・energy2 は実装しない。カードの選択の表示は本人の手札だけで決まるので返す。読む情報を確かめていない使うための条件は呼ばず、処理可能性で示す（unverified）。F-9 の今の扱い（公開の情報だけで使えない場合も決定を出す）は変えない
    - `D-U75-POWER`: U7-5e（2026-11-08 の依頼）: UsePokemonPower を、型ごとの宣言の入力（D-U75-INPUT-DECL）と 2〜3 段の依存する入力（D-U75-CHAINED）で扱う。CheckFaceUpDeckCard・energy2・R-2 は実装しない。相手のうらのカードは公開の位置だけで示し、指定する組は unverified（D-U75-POWER-FACE-DOWN）
    - `D-U75-STADIUM`: U7-5d（2026-11-08 の依頼）: 場のスタジアムの UseStadium だけを扱い、特殊能力・CheckFaceUpDeckCard・energy2 は実装しない。候補は使ってよい効果の登録（activated）から作り、選ばせるものは型の宣言（energy_choice）から作る。3 段の入力の基盤は先に作らない。キョウの忍者ジムの保守的な NJ1 は緩めない
    - `D-U75-FACE-UP-ACTORS`: 初版の U7 では、CheckFaceUpDeckCard を番のプレイヤー（MAIN）だけに表示する。既存のコマンドの主体の制約ではなく、API の対応の範囲として記録する（coverage の residual R-4。U7-5f で実装）
    - `D-U75-ENERGY2-SCHEMA`: カツラの 2 枚目は attach_energy の任意の 3 段目とし、1・2 段目の組で引く options_by_path（path_stages）で示す。経路の表し方・既存の項目との併用・参照の確かめを固定する（U7-5g で実装）
    - `D-U75-FACE-DOWN-POWER`: 本人が知る印刷の情報だけから安全に作れる特殊能力を候補にする。unverified だけを理由に公開を許さない（U7-5g で実装）
    - `D-U75-R2`: R-2 は今回も未対応のまま残す（coverage の residual で示す）
    - `D-U7-COMPLETENESS`: residual を機械で読める形で返す。未対応の宣言の経路が残るあいだ MAIN は partial のまま。候補の取得の網羅と、全部の操作の完走を分ける（U7-5g で実装）
  - 実装した単位: `U7-5a`、`U7-5b`、`T-F1`、`U7-5c`、`U7-5d`、`U7-5e`、`U7-5f`
  - 仕様の訂正:
    - `CORR-1`（E 群の意味）: 情報源が未確認の経路を、処理可能性の unverified だけで公開してよいと扱わない。処理可能性と入力の公開の安全性は別の軸。選べるもの・件数・理由を公開して安全と確かめられないなら、入力は返さない（unconfirmed）。型・生成箇所の登録だけで安全と認めない
    - `CORR-2`（GUI への影響の比べる相手）: 設計の報告の d0c5cfa はエンジンのコミット（GUI の main が固定するエンジン）で、GUI のコミットではない。公開されている最新の GUI は feature/engine-u7-4-attacks の 3649946（エンジン 9506d63・0.166.0 を固定）。GUI のコミットと固定するエンジンを分けて書く（GUI_REF）
    - `CORR-3`（GUI の比べる相手と 3 段の入力の互換性（2026-11-08））: v0.171 の文書は 3649946 を今の GUI として書いていた。最新の公開の作業ブランチは feature/engine-u7-5-trainers-stadium の 9c36a8f（エンジン 0885d66・0.170.0 を固定）。3 段の入力の「新しい項目を無視するクライアントでも正しい組だけを選べる」は、depends_on_stage が指す段の選ぶもので options_by_choice を引くクライアントだけに成り立つ（U7-3 を前提に 1 段目で引くクライアントは閉じた側の失敗、options_by_choice を使わないクライアントの安全はサーバの入力の検査による。docs/legal-actions-u7-5fg-spec.md 0 章）
<!-- generated:rest-record end -->

## 1. 単位

<!-- generated:rest-units begin -->
| 単位 | 状態 | 名前 | コマンド | 依存 | 変更範囲 | 完了の基準 | GUI への引き継ぎ | 残る事項 |
|---|---|---|---|---|---|---|---|---|
| `U7-5a`（最初） | `implemented`（v0.167（docs/legal-actions-u7-5ab.md）） | 場のポケモン 1 匹を指す操作（RemoveDisguise・DiscardFromPlay） | `RemoveDisguise`<br>`DiscardFromPlay` | U7-4 | engine.py: 2 つの処理の受理の前の部分を、同じ順番・同じコード・同じ文のまま check_remove_disguise・check_discard_from_play にする（U7-3 の check_* と同じ）<br>legal_actions.py: 2 種類の候補（1 段・choose_option・場のポケモンの番号）。うらのカードは DiscardFromPlay の候補に出さない（F-2 の FD1 に当てない） | 2 種類が evaluated になり、MH1・TK1 に当たる候補は may_stop_later、DiscardFromPlay は U7-3 と同じ条件でだけ supported。直接のコマンドとの一致・双子（うらのカードの本当のカード）が通る | 1 段の choose_option（場のポケモンの番号）。決定への接続は promote_active の候補（空いたバトル場） | なし |
| `U7-5b` | `implemented`（v0.167（docs/legal-actions-u7-5ab.md）） | うらのカード（RevealFaceDown） | `RevealFaceDown` | U7-5a | engine.py: _reveal_face_down の受理の前の部分を check_reveal_face_down にする<br>legal_actions.py: 1 段の候補。候補に結果（残るか）を書くかは D-U75-REVEAL-OUTCOME | 相手・観戦者の応答が、本人のうらのカードの本当のカードで変わらない双子（たね・たねでない）が通る。おもてにしたあとのログが観測の規則どおり | 1 段。おもてにしたあとの公開のログ（secret_plan_revealed・secret_plan_discarded）の表示 | なし |
| `T-F1` | `implemented`（v0.168（docs/chaos-gym-borrow-t-f1.md。サイキックコントロールの F-8 もいっしょに直した）） | 錯乱ジムの情報漏れ F-1 の修正（両モード共通の不具合。トレーナーの前の独立した作業） | なし | U7-5b | effects.py: borrow_public_unusable_reason・borrow_condition_stop・require_borrow_playable（公開の部分と、使う人だけが知る使うための条件を分ける）。サイキックコントロールの選べるもの・答えの確かめ<br>engine.py: _chaos_tails（公開の分岐）・_resume_trainer（「使う」の答えの確かめ） | 相手の手札の中身だけを変えた双子で、使ったプレイヤー・観戦者が受け取る公開の情報が一致する。2 つのモードで同じ扱い | 錯乱ジムの「うら」のあとは、使えない人にも決定が出る。「使う」の拒否は答えた人にだけ返る | F-9（公開の情報だけで満たせないと分かる使うための条件を、公開の分岐に戻すかの判断と監査） |
| `U7-5c` | `implemented`（v0.169（docs/legal-actions-u7-5c.md）） | 手札のトレーナー（PlayTrainer） | `PlayTrainer` | U7-5b<br>T-F1 | engine.py: _play_trainer の手札から出す前の部分を check_play_trainer にする（同じ順番・同じコード・同じ文。use_condition が偽なら使うための条件だけを呼ばない）<br>legal_actions.py: 1 段の候補 play_trainer（選べるものは本人の手札のトレーナーカード）。登録なしは not_implemented、停止は診断のコード表の分類。使うための条件を呼ばないカード（PLAYABLE_NOT_EVALUATED）は unverified（入力は本人の手札だけで決まるので返す。条件の結果で選べるものを選り分けない） | A-own の 6 の実装で双子が通る。錯乱ジムの「うら」・［ちえくらべ］・サイキックコントロールは受理のあとの決定として new_game からの列でつながる。E のうち読む値をたどっていない 5 の実装は、使うための条件を呼ばず unverified（対応済みに数えない） | 1 段。受理のあとの決定の種類が多い（検索・見たカード。U7-1 の DECK_REVEALING_KINDS の契約の例外） | PT-5e の 5 の実装（実際の山札から引いて試す）の読む値をたどる<br>effects.py の外の閉包（PT-5t・A 群の呼ぶ別のモジュールの関数の 2 段目より先） |
| `U7-5d` | `implemented`（v0.170（docs/legal-actions-u7-5d.md）） | 場のスタジアム（UseStadium） | `UseStadium` | U7-5a | engine.py: _use_stadium の check_activation までを check_use_stadium にする（同じ順番・同じコード・同じ文）<br>effects.py: StadiumEffect.energy_choice（選ばせるものの宣言。挙動は変えない）<br>legal_actions.py: use_stadium。使ってよい効果（activated）だけ。選ばせるもののない候補と、energy の 1 段の候補 | 持ち主でないプレイヤーの使用・同じ番の 2 回目（STADIUM_ALREADY_USED・LK1）・キョウの忍者ジムの双子が通る | 選ばせるもののない候補と 1 段の候補 | キョウの忍者ジムの保守的な NJ1（山札の外の見えないカードの数より多くキョウのたねポケモンがないと止める。v0.146 のまま）<br>check_activation が呼ぶ別のモジュールの関数の 2 段目より先 |
| `U7-5e` | `implemented`（v0.171（docs/legal-actions-u7-5e.md）） | 宣言する特殊能力（UsePokemonPower） | `UsePokemonPower` | U7-5b<br>U7-5d | effects.py: 型ごとの選ばせるものの宣言（D-U75-INPUT-DECL。挙動は変えない）<br>engine.py: _use_pokemon_power の宣言の前の部分を check_use_pokemon_power にする（_reveal_for_action の扱いは D-U75-POWER-FACE-DOWN）<br>legal_actions.py: 特殊能力の位置ごとの候補 → 選ばせるもの（0〜3 段） | 形ごとに 1 つ以上の代表で、宣言の入力・受理のあとの決定・回数の制限が通る。相手のうらのカードは公開の位置・識別だけで扱う（ADOPT-U7-5AB）。E の 7 の実装は、たどるまで入力を返さない（CORR-1） | 2〜3 段（depends_on_stage = 2。前の段を変えたら、それに依存する後の段をすべて無効にする。ADOPT-U7-5AB） | 名前で解決できない呼び出し（状態のメソッド・登録表の引き・正規表現）の先（UP-5t）<br>自分のうらのカードの特殊能力（候補にしない。R-2 と同じく残る） |
| `U7-5f` | `implemented`（v0.172（docs/legal-actions-u7-5fg.md 1 章）） | おもての山札の確かめ（CheckFaceUpDeckCard） | `CheckFaceUpDeckCard` | U7-5a | legal_actions.py: 番のプレイヤーの MAIN に、相手の山札のおもての 2 枚目より下の位置（owner・position。カード id・uid を出さない）を unresolved_ruling で示す（送る前に CANDIDATE_NOT_EXECUTABLE。エンジンに渡さない） | 候補の位置が、おもての枚数（公開）だけで決まる双子（おもてのカードの中身を変える）が通る | 表示だけ（送信のボタンを出さない） | なし |
| `U7-5g` | `planned` | 残りの経路と coverage の閉じ方 | なし | U7-5c<br>U7-5e<br>U7-5f | R-1（カツラの 2 枚目）を attach_energy の任意の段として加える（ADOPT-U7-5AB で採用。3 段目の引き方は D-U75-ENERGY2-SCHEMA）・R-2 の見直し（D-U75-R2）<br>自分のうらのカードの特殊能力（D-U75-FACE-DOWN-POWER）<br>段階・主体ごとの coverage の表し方（C-6。residual・unverified_paths。D-U7-COMPLETENESS） | C-1〜C-6 を満たすかを、単位ごとの結果から判断できる（U7-5g-1〜3 の完了の基準は docs/legal-actions-u7-5fg-spec.md 6 章） | coverage の表示 | D-U7-COMPLETENESS<br>D-U75-ENERGY2-SCHEMA<br>D-U75-FACE-DOWN-POWER<br>D-U75-R2 |
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

## 3. 最初の単位: U7-5a（RemoveDisguise・DiscardFromPlay）。v0.167 で U7-5b といっしょに実装

この章は実装の前に書いた具体化です。実装の結果（意図した差・直した U7-3 の候補の失敗 F-7・JSON の実例）は [legal-actions-u7-5ab](legal-actions-u7-5ab.md) にあります。実装では、本人のうらのカードを `DiscardFromPlay` の選べるものから除かず、エンジンの確かめの判定（FD1 の `UnsupportedError`）どおり実行できない区分で示しました（ゲーム上の禁止として消さない）。

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
  - 選べるものは自分の場のポケモンで、関数の確かめで ILLEGAL のものは出しません（実装では、本人のうらのカードはエンジンの判定どおり FD1 の停止として示した）
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
| `T-F1` | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） |  | 構築盤面（build_test_state） | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） | 構築盤面（build_test_state） | 構築盤面（build_test_state） | new_game からの合法な操作列 | new_game からの合法な操作列 | 構築盤面（build_test_state） | 補助関数だけの確かめ（候補の作成を直接呼ぶ） |
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
