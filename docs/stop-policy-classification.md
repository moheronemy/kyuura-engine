# 停止コードと未対応処理の分類（厳密モード・プレイ用モードの将来の導入に向けて）

この文書は調査・分類・設計の記録です。モードの実装、既存の動作の変更、裁定の変更はしていません。エンジン・既存のテスト・カードの登録・保存形式・固定デッキ・過去の参照データ・
kyuura・利用者の `.claude/` は変えていません。ここに書く方針は**どれも案で、利用者の承認を受けていません**（分類の時点の記録）。その後、2026-11-03 にモードの定義の 6 項目を利用者と
合意しました（7.6 節・[ruleset-mode-design.md](ruleset-mode-design.md) 2 章）。合意したのはその 6 項目だけで、族の候補・個々の続行規約は今も案です。

- 構造化台帳: [stop-policy-classification.json](stop-policy-classification.json)（`scripts/build_stop_policy_classification.py --write` で作り、`--check` で現行コードと突き合わせる）
- 利用者が決める事項: [stop-policy-decisions.md](stop-policy-decisions.md)（個々の停止コード・族）・[ruleset-mode-decisions.md](ruleset-mode-decisions.md)（規約集合とモード）
- 規約集合の設計: [ruleset-mode-design.md](ruleset-mode-design.md)
- 後の版の経過: 7.4 節（v0.137 で PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE を修正。ST1・FC1 の論点・モードの方針は未決のまま）・7.5 節（v0.138 で PSP-RUIN-WALL-BLOCKED-REASON-ORACLE・PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE を修正。新しい発見 2 件は未修正）・7.6 節（2026-11-03。モードの定義の合意と、規約集合の設計）
- 元の棚卸し（v0.133 時点。基点・集計は書き換えず、履歴として参照する）: [pre-freeze-gap-inventory.md](pre-freeze-gap-inventory.md)・[JSON](pre-freeze-gap-inventory.json)・
  [修正計画](pre-freeze-remediation-plan.md)

## 1. 基点と作業の保護

| 項目 | 値 |
|---|---|
| 基点 | `3e25ac5eff0f90dbea224045e77c2b60e025bf2d`（v0.136 の最後のコミット。版 0.136.0。`origin/claude/v0.136-card-flip-game` と同じ） |
| 基点が含むもの | v0.134 `991db7b`（main にマージ済み。PR #28）、v0.135 `450c2be`・`da9d4e9`（PR #29 は未マージ）、v0.136 `a81952f`〜`3e25ac5` |
| `origin/main` | `07acf1788321e068a3582c284418ef618ed86a42`（v0.134 のマージ）。基点の祖先。v0.135・v0.136 を含まない |
| 作業ブランチ | `claude/stop-policy-classification`（基点から作った） |
| 後続の変更 | 作業の開始時に `git fetch` で確かめ、v0.136 より後の公開ブランチ・コミットはなかった。未コミットの変更は利用者の `.claude/`（追跡していない）だけで、変えていない |
| kyuura（エンジンが参照する固定コミット） | `71d1728938fb4c8fefde9b82779cdef74beb612d`（`scripts/extract_kyuura_cards.py` の `KYUURA_COMMIT`・`research_links.json` の `research_commit`・`card_data_commit`） |
| kyuura（調査で見た checkout） | `C:/dev/kyuura` の `b9e7cff6d2b2c6b4539ec45e61bf453879adab3a`（main。未コミットの変更なし）。固定コミットの祖先（固定コミットより古い）。読んだだけで、分類の根拠には固定コミットの記録（エンジンの写し）を使った |

`origin/main` だけを基準にすると、v0.135・v0.136 で直したクイズ・カードめくりゲームの漏れを未修正と読み違えるので、基点は v0.136 の最後のコミットにしました。

### 1.1 v0.133 の棚卸しからの経過（現行コードで確かめたこと）

| 経過 | 現行コードでの確認 | 台帳での扱い |
|---|---|---|
| サドン・デスの延長戦の開始（v0.134） | `StartSuddenDeath`（`engine._start_sudden_death`）。サドン・デスの状態にほかのコマンドを送ると `IllegalActionError` `SUDDEN_DEATH_NOT_STARTED`。`SUDDEN_DEATH_NOT_IMPLEMENTED` はコメントだけに残る。新しい停止コード `UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK`（`sudden_death.py:26`）、内部ガード `engine.py:445`（開始の前の不変条件） | 棚卸しの P0 は `fixed`。新しいコード・ガード・利用者指定 `USER-SUDDEN-DEATH-OWNERSHIP-RESET` を加えた |
| クイズその2・その3・ポケモン性格判定の漏れ（v0.135） | `effects.quiz_draw_outcome_stop` が使う前に正誤の両方の引き方を確かめる | `GAP-QUIZ2/QUIZ3/PERSONALITY-REJECTION-ORACLE` は `fixed`。保守的な止め方は `UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#quiz-precheck` の事例。FU3 は未解決 |
| カードめくりゲームの漏れ（v0.136） | `GuessOpponentPrizeKind.face_up_draw_stop`（`outcomes` を渡す） | 棚卸しの `post_audit_entries` の `GAP-CARD-FLIP-REJECTION-ORACLE` は `fixed`。FU3 は未解決 |

## 2. 方法

1. **静的な全件の抽出**（`scripts/stop_policy_scan.py`）
   - `UNSUPPORTED_*`・`UNRESOLVED_*` を、tokenize で文字列リテラル・コメント・識別子に分けて集めた。
   - `NAME = "CODE"` の定数を別名として解決した。
   - 接頭辞のない `UnsupportedError` のリテラル、内部ガード（`raise RuntimeError`・`NotImplementedError`・`AssertionError`・`StateIntegrityError`・`UnsupportedByKernel`）、
     `Phase.HALTED`・`Halt(`・`halt(`・`interrupt(` の箇所も抽出した。
2. **止め方の分類**
   - `Halt(code=…)` と `check_quantity(code=…)` に渡す定数から、準備の HALTED・ポケモンチェックの HALTED・途中停止を特定した。
   - それ以外の `UnsupportedError` は「コマンドの拒否」とした。決定でどの答えも止まるときに HALTED に変わる共通処理（`engine._apply_once`）を含む。
   - `error.code` を渡す動的な変換（ポケモンチェックの途中・決定の答え）は、コードごとには特定していない。
3. **到達可能性**
   - `legal_sequence`: 対戦の道具の記録（`C:/dev/kyuura-engine-verification` の v0.134〜v0.136 の検証の証拠 51 ファイル。sha256 は台帳の `evidence`）で観測したもの。
     道具は `new_game` の固定デッキから、合法なコマンドだけを送る。
   - `constructed_board`: 比較プローブで確かめたもの、またはテストに表明らしい行（`assert`・`Raises`・`.code`）があるもの。
   - `static_only`: それ以外。
   - テストの行は静的な分類で、行の実行・隣の受理枝は計測していない。同じ指紋のコードで v0.136 の全体のテスト（7,282 件・失敗 0）が通っている。
4. **棚卸しとの対応**
   - コード・問題の ID は棚卸しの ID をそのまま使った（`inventory_ref`）。
   - 内部ガード 602 箇所は、(ファイル, 文, 関数の名前) で棚卸しの `GUARD:*` 600 件と対応させた。全件が対応し、残る 2 箇所は棚卸しの後に加わったもの・棚卸しの型の集合の外だったもの。
5. **漏れの横断**
   - 使う前の確かめ（`check_playable`・`check_usable`）のうち、山札・サイドを読んで `UnsupportedError` を投げる 19 クラスを AST で抜き出した。
   - そのうち中身を読む 2 つを、エンジンを変えない比較プローブ（`tests/log_audit.py` の `twin_command_problems`）で確かめた（付録 A）。

UNRESOLVED という名前は、公式資料を十分に調べた結果だとは断定しません。台帳の `research.checked` には「固定研究基準の対応表とエンジンの記録を参照しただけ。公式資料の再調査・kyuura の後続の記録の照合はしていない」と書きました。

## 3. 分類の軸

- **A〜E**（棚卸しの分類をそのまま保持）: A=機能不足、B=技術的制限、C=公式情報から未裁定として扱っているもの、D=明示的な独自規約で処理済み、E=その他。モードの方針とは別の軸です。
- **プレイ用の対応群**（1〜6）: 1=規約で続行できる、2=プレイヤーの選択の実装で続行できる（選ぶ人が未裁定なら 1 が先）、3=機能・データの追加が要る、4=計算・探索の改善が要る、
  5=両モードで保護・拒否が要る、6=対象外・将来拡張・追加確認待ち。群に入れても規約を採ったことにはしません。
- **止め方**:

  | 止め方 | 意味 |
  |---|---|
  | `command_rejection` | コマンドを受け付けない（状態は変わらない）。どの答えでも止まる決定なら、その前の状態で HALTED |
  | `answer_rejection` | 答えの一部だけ受け付けない |
  | `setup_halt` | 準備で止まる |
  | `pokemon_check_halt` | ポケモンチェック・番の終わりで止まる |
  | `deferred_interruption` | 途中停止 |
  | `deck_validation` | デッキの検査で拒否 |
  | `not_raised` | 現行では投げない |
- **到達可能性**: `legal_sequence`・`constructed_board`・`test_only_mutation`・`static_only`・`unknown`。根拠なしに到達不能とした項目はありません（`--check` が確かめる）。
- **状態**: `active`（現在有効）・`fixed`（修正済み）・`historical`（履歴項目）・`unverified`（未確認の候補）。
- **方針の状態**: 今回の台帳は `unconsidered`（未検討）・`proposal`（案）・`decision_required`（利用者の判断が要る）だけを使います。既存の利用者指定の挙動の状態（承認・実装・検証）は
  `existing_behavior_status` に別に書きます。

## 4. 集計

停止コード・事例・規約・内部ガードは、それぞれ別の数です。事例はコードの下位なので、コードの数には足しません。棚卸しと同じ項目は、独立した不足として数えていません。

| 対象 | 件数 | 内訳・注記 |
|---|---:|---|
| 研究の停止コード（固定研究基準の対応表） | 316 | 全件 C。全件が現行のエンジンにある |
| 表外の停止コード（現在有効） | 39 | A 32・B 5・E 2（汎用 `UNRESOLVED_RULING`、デッキの検査の `UNSUPPORTED_CARD`）。v0.133 の後に加わった `UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK` を含む |
| 表外のコード（履歴） | 1 | `UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER`（コメントだけ。v0.34 で解消） |
| テスト・道具だけのコード | 8 | 合成した登録表・比べの印・文字列の断片。エンジンでは投げない |
| 事例（コードの下位） | 15 | 7 コード（ST1・FC1・FU3・切り直しの補償・PF1・GV1・SC1） |
| 新しく見つけた項目 | 3 | 漏れ 2（確認済み）・漏れの候補 1（静的。未確認） |
| 棚卸しの構造上の問題・コードなし論点の参照 | 28 | うち修正済み 5（クイズ 3・カードめくりゲーム 1・サドン・デスの P0 1）、履歴 1 |
| 採用済みの規約（利用者指定・簡略化・実装上の仮定） | 18 | 棚卸しの 16 件と、後に加わった `USER-SUDDEN-DEATH-OWNERSHIP-RESET`、棚卸しにない利用者のデータの修正（PR1-069 の名前） |
| 内部ガード（現在） | 602 | RuntimeError 588・NotImplementedError 10・StateIntegrityError 3・UnsupportedByKernel 1。棚卸しの 600 件と全件が対応、新しい 2 箇所（`engine.py:445` は v0.134、`programs.py:10739` は棚卸しの型の外の既存の箇所） |
| 安全境界（ガード・原則のまとめ） | 8 | 9 章 |

現在有効な停止コード 355 件（研究 316＋表外 39）の到達可能性:

| 到達可能性 | 件数 |
|---|---:|
| `legal_sequence` | 25 |
| `constructed_board` | 145 |
| `static_only` | 185 |

`static_only` は「発生を確かめていない」という意味で、到達しないという意味ではありません。

止め方（1 つのコードに複数の止め方があれば、それぞれ数える）:

| 止め方 | コード数 |
|---|---:|
| コマンドの拒否 | 339 |
| 答えの一部の拒否 | 13 |
| ポケモンチェックの HALTED | 10 |
| 準備の HALTED | 2 |
| 途中停止 | 2 |
| デッキの検査 | 1 |

## 5. 止まり方と、道具の対戦で起きている停止

対戦を終端にする止め方（HALTED・途中停止）は、次の 14 コードに静的に特定しました（ほかの拒否が動的に HALTED に変わる経路は別）。

- **準備**: `UNRESOLVED_MULLIGAN_COMPENSATION`・`UNRESOLVED_PLAY_AS_POKEMON_SETUP`（どちらも最初の対戦と延長戦の区間）
- **ポケモンチェック・番の終わり**:
  - `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`・`…_DOUBLE_KNOCKOUT`・`…_MID_KNOCKOUT`・`…_BERRY_ORDER`・`…_CHAR_COIN_ORDER`
  - `UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`
  - `UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`・`UNRESOLVED_SCRAM_TIMING`・`UNRESOLVED_LEAVE_LOCK_KNOCKOUT`・`UNRESOLVED_LEAVE_LOCK_SCRAM`
- **途中停止**: `UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`（DU1）・`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT`（TW1）。再開の操作はない（`GAP-DEFERRED-HALT-NO-RESUME`）

道具の対戦（初期状態からの合法な操作の列）で観測した 25 コードのうち、対戦を止めたのは次の 2 つでした。

- `UNRESOLVED_MULLIGAN_COMPENSATION`（準備）
- `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`（ポケモンチェック）

残りの 23 コードは、道具が試した操作の拒否でした（ほかの操作を選んで対戦は続いた）。拒否の多いもの:

- こんらんのダメージとプラスパワー・ディフェンダー（`CONFUSION_DAMAGE_MODIFIERS`）
- フラッシュの山札（`FACE_UP_DECK_HIDDEN_TAKE`）
- きあいのハチマキの時点（`FOCUS_BAND_TIMING`）
- 返すダメージでの両方のきぜつ（`RETALIATION_DOUBLE_KNOCKOUT`）
- 変身のエネルギーの数（`TRANSFORM_ENERGY_COUNT`）
- 変身がもどるときのきぜつの時点（`TRANSFORM_REVERT_KNOCKOUT_TIMING`）

（数は同じ束の基点・現在の重複を含むので、台帳はファイルごとに記録した。）錯乱ジム×ちえくらべ（MG1）は、v0.132 の正式な対戦の記録による `legal_sequence` です。

モードの導入では、**対戦を止める止め方（とくに準備の HALTED）と、選択肢を 1 つ減らすだけの拒否を分けて優先度を付ける**のが妥当です。プレイ用モードの効果が大きいのは前者ですが、
拒否の頻度が高いもの（ダメージの範囲・時点）は、規約の影響が広くなります。

## 6. 族ごとの要約

族は方針を書く単位で、コードの改名・実装上の分割はしていません。各族の厳密モード（2 案）・プレイ用の候補（対象・時点・範囲・結果の違い・安全条件）・必要な研究・判断・実装・危険・
回帰検証は、台帳の `families` に書きました。

| 族 | コード | 観測・構築・静的 | 対応群 | プレイ用の候補の要点 |
|---|---:|---|---|---|
| PF-USE-WITHOUT-EFFECT（対象・効果がないときの使用） | 57 | 0・16・41 | 1 | 使えない／使えて何もしない（コードごと）。非公開の領域に依存するコードは「使えない」で漏れが残る |
| PF-UP-TO-ZERO（「最大N」の 0） | 13 | 0・8・5 | 1・2 | 0 を選べない／選べる |
| PF-STATED-COUNT-SHORT（数の不足） | 11 | 0・4・7 | 1 | あるだけ処理する／使えない。ひかるバンギラスの指定は広げない |
| PF-SIMULTANEOUS-ORDER（順番・決める人） | 26 | 3・14・9 | 1・2 | 席によらない規則で固定／選ばせる（選ぶ人が先）／全順番で同じなら続ける |
| PF-KNOCKOUT-TIMING（きぜつの時点） | 15 | 5・8・2 | 1 | 読み方の固定。勝敗が変わる |
| PF-EFFECT-TIMING（効果の時点） | 13 | 2・6・5 | 1 | 時点の固定 |
| PF-PROTECTED-TARGET-EFFECT（無効な要素のコイン） | 12 | 2・4・6 | 1 | 投げる／投げない。乱数の列がずれる |
| PF-DAMAGE-SCOPE（ダメージの範囲） | 22 | 2・10・10 | 1 | 当てはめる／当てはめない |
| PF-ENERGY-TYPE（エネルギー・色） | 21 | 3・8・10 | 1 | 読み方の固定 |
| PF-COPY-TRANSFORM（コピー・変身） | 34 | 2・10・22 | 1・3 | 規約と実装の両方が要る |
| PF-HISTORY-LASTING（記録・持続する効果） | 20 | 3・5・12 | 1・3 | 続く／終わる。旧状態の記録の不足は推測しない |
| PF-TEXT-READING（説明の読み方） | 34 | 0・15・19 | 1 | 読み方の固定（同じ言い回しの別のカードに広げない） |
| PF-REACTION-DURING-PROCESS（途中の反応） | 10 | 0・5・5 | 1・3 | 使える場合は反応の継続の実装が要る |
| PF-POWER-SUPPRESSION（特殊能力を消す範囲） | 11 | 0・4・7 | 1 | 及ぶ／及ばない。循環を席で切らない |
| PF-SETUP-PLAY-AS-POKEMON（準備・化石・人形） | 5 | 2・1・2 | 1 | 切り直しの補償の数え方・引く時点 |
| PF-HIDDEN-INFORMATION（うら・おもての山札） | 8 | 1・3・4 | 1・5 | 読み方を決めても、秘密への非依存を確かめ直す |
| PF-ESP-REDO（ESP のやり直し） | 4 | 0・3・1 | 1 | やり直せる・やり直せない |
| PF-RUNTIME-REGISTRY（登録・契約のガード） | 7 | 0・5・2 | 5 | 候補なし（未登録を推測で進めない） |
| PF-RUNTIME-COPY-GAPS（コピーの実装の不足） | 5 | 0・3・2 | 3 | 候補なし（実装の不足） |
| PF-RUNTIME-CONTINUATION（継続の実装の不足） | 15 | 0・6・9 | 3 | 候補なし（継続の状態がない） |
| PF-RUNTIME-SEARCH-LIMIT（探索の上限） | 6 | 0・3・3 | 4 | 候補なし（枝を削らない。計算の改善） |
| PF-RUNTIME-DATA（属性・旧形式） | 5 | 0・4・1 | 3・5 | 候補なし（推測で埋めない） |
| PF-RUNTIME-GENERIC（UNRESOLVED_RULING） | 1 | 0・0・1 | 6 | 未検討（どの問いか分からない） |

## 7. 新しく見つけた項目（今回の調査で。修正はしていない）

### 7.1 PSP-ST1-DECK-ORACLE（確認済みの漏れ。構築盤面）

山札から決まったカードを選ぶトレーナーで、選ばなくてよいと書かれていないもの（エネルギー転送 PMCG3-044・ボスのやりかた・タケシの育て方）と、遺跡の石版（neo2-054・neo2-057）は、
使う人の山札に選べるカードがないと、使う前に `UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET` で拒否します（`effects.py:17289`・`:39921`）。

山札とサイドの中身は使う人にも見えないので、この拒否は「目的のカードが山札にない（＝サイドか、ほかの見えない場所にある）」ことを、カードを使わずに教えます。
比較プローブでは、炎エネルギーが山札にある盤面とサイドにある盤面で、プレイヤー 0 の公開の情報が同じことを確かめました。そのうえで同じ `PlayTrainer` が、前者は受理、
後者は ST1 で拒否になり、`twin_command_problems` が段 0 で検出しました。拒否は状態を変えないので、毎番くりかえせます。

v0.135・v0.136 の漏れと同じ型（受理・拒否による漏れ）です。トラッシュを選ぶリサイクル（`:17502`）は公開の情報なので、事例を分けました（`#deck`・`#discard`）。

### 7.2 PSP-FC1-ENERGY-ARK-ORACLE（確認済みの漏れ。構築盤面）

エネルギーアーク（neo2-053）は、山札の基本エネルギーカードがコインの枚数（2）より少ないと、使う前に `UNRESOLVED_STATED_CARDS_SHORT` で拒否します（`effects.py:31101`）。
山札に 2 枚ある盤面は受理、1 枚が山札・1 枚がサイドの盤面は FC1 で拒否になりました（プローブで検出）。FC1 のほかの 7 か所は枚数（公開）を読むので、事例を分けました。

### 7.3 PSP-DECK-CONTENT-PRECHECKS（漏れの候補。静的な確認だけ）

使う前の確かめで山札の中身を読むほかの経路です。比較プローブはしていないので、漏れとも安全とも数えていません。

- `CoinEvolveSelfFromDeck.check_usable`（`effects.py:12375`）: 山札の同じ名前のカードで GV1・DV2・`UNRESOLVED_EVOLUTION_HP` を判定する
- `BenchNameGroupFromDeckTrainer` の `bench_entry_unresolved`（`:39924`）: 山札の候補のどれもベンチに出すと止めるなら止める

熱血!（FV1。`:29159`）は山札とサイドを合わせて読むので、分け方には依存しません（候補から外した）。

この 3 項目は、モードによらず塞ぐべき漏れです（10 章の SB-SECRET-INDEPENDENCE）。PF-USE-WITHOUT-EFFECT の「使えない」（P-UWE-1）や PF-STATED-COUNT-SHORT の「使えない」（P-SCS-2）を
規約にしても、漏れは塞がりません。

### 7.4 v0.137 での経過（2026-11-02。上の 7.1〜7.3 の発見の記録・基点・集計は変えていない）

利用者の承認は「情報漏れ 2 件を先に修正すること」だけです（厳密モードの定義・不足時の規約・プレイ用の規約の承認ではありません）。[deck-search-oracle-v0.137.md](deck-search-oracle-v0.137.md)。

- **PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE は修正済み**（台帳の status は `fixed`）。使う前の確かめを、実際の山札の候補から、配分を読まない下限
  `effects.deck_target_lower_bound`（本人に見えない自分のカードのうち目的のカード K 枚・山札の外の見えないカード C 枚から max(0, K − C)）に替えました。下限が足りなければ既存の
  ST1・FC1 のまま使う前に止めます（実際には山札にある場面も止める保守的な制限）。理由の文は決まった文です
- **ST1・FC1 の研究上の論点は未解決のまま**です。研究の停止コードは `active` のまま（停止コードを修正済みにしない）。事例 `#deck`・`#deck-contents` の `secret_dependency` は
  `owner_known_pool`（本人が知っている集合と公開の枚数だけで決まる）にしました
- K の集合は持ち主のデッキリストと所有者の変更から持ち主が知っている値で、エンジンの観測には入っていません。受理（公開）は相手・観戦者に「見えないカードに C + 必要な枚数以上ある」ことを
  伝えます（分類の時点は「山札に必要な枚数ある」）。どちらも使ったプレイヤーの非公開の情報で、相手は試せません（版の文書 4.3・4.4 節）
- 7.3 節の候補を比較プローブで確かめ、遺跡の石版の「山札の候補がどれもベンチに出すと止める」拒否の理由の文が山札のカードの名前・uid を書く漏れ（PSP-RUIN-WALL-BLOCKED-REASON-ORACLE）と、
  同じ型の横断でエネルギー増幅装置（neo4-102）の UPZ2 の漏れ（PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE）を見つけました。どちらも修正していません（台帳に `active` で追加）。キョウのコクーンの経路は
  未確認の候補のままです
- 台帳の作成スクリプトの直した点: 2 項目の修正の記録、新しい 2 項目、`updates`（この版の基点 897103e と変えた項目）、`counts_at_classification`（分類の時点の集計の写し）、事例の行番号、
  リポジトリのファイルの sha256 を改行を LF にそろえて求めること（分類の時点の `research_reference.sha256` は CRLF の作業の木の値。内容は同じ）

### 7.5 v0.138 での経過（2026-11-03。7.1〜7.4 の記録・基点・集計は変えていない）

利用者の承認は「v0.137 で新たに見つかった 2 件の情報漏れを、モード共通の不具合として修正すること」だけです（厳密モードの定義・プレイ用の規約・検索の不足時の処理の承認ではありません）。
[oracle-leak-fixes-v0.138.md](oracle-leak-fixes-v0.138.md)。

- **修正した情報漏れの範囲**: PSP-RUIN-WALL-BLOCKED-REASON-ORACLE（遺跡の石版のガスのもとの使う前の拒否の理由の文。受理・拒否・コードは修正の前も配分によらなかった）と
  PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE（エネルギー増幅装置の使う宣言と段階 1 の答えの UPZ2）。台帳の status は `fixed`。どちらも配分を読まない下限（`effects.bench_entry_unconfirmed`・
  `deck_target_lower_bound`）で確かめ、既存のコードのまま決まった文で止めます
- **依然残る情報伝達・未確認の候補**: 受理（公開）が相手・観戦者に、使ったプレイヤーの見えないカードの構成の 1 ビットを伝えること（v0.137 4.4 節・v0.138 5.4 節）。比較プローブで新しく
  見つけた PSP-INCREASE-ENTRY-PW3-ORACLE（［INCREASE］の使う機会）・PSP-COCOON-DV2-ORACLE（キョウのコクーンの［うか］の DV2）は修正していません（`active`）。PSP-DECK-CONTENT-PRECHECKS の
  残り（GV1・EVOLUTION_HP の経路）は未確認の候補のままです
- **未解決の裁定**: GG1・MG1・DW1・UPZ2・ST1 などの研究の停止コードは `active` のまま（停止コードを修正済みにしない）。UPZ2 に事例 `#amplifier-deck`（`owner_known_pool`）・
  `#public-zones` を加えました
- **保守的な使用制限**: 増幅装置は、実際には山札に基本エネルギーカードがあっても、下限 0 なら特殊エネルギーカードをもどせません（手札がそれだけなら使えません）。遺跡の石版は今の写しでは
  受理・拒否が変わりません（止めないカードと止めるカードが混ざる候補で、実際には山札にあっても止める制限が共通処理にある）
- **厳密モードの定義は未決**です（DEC-STRICT-DEFINITION ほか）。この版の承認をプレイ用の規約・モードの定義の承認へ広げていません
- 台帳の作り直しで、既存の 173 項目の行番号が変わりました（effects.py の編集で行がずれただけ。意味は変わらない。版の文書 10 章）

### 7.6 モードの定義の合意と、規約集合の設計（2026-11-03。7.1〜7.5 の記録・基点・集計は変えていない）

利用者と、モードの定義の 6 項目を合意しました（台帳の `mode_agreements`。根拠は本会話の利用者の指示で、公式の裁定・kyuura の研究上の解決ではない）。設計と残る判断事項は
[ruleset-mode-design.md](ruleset-mode-design.md)・[ruleset-mode-decisions.md](ruleset-mode-decisions.md) にあります。エンジン・既存のテスト・カードデータ・保存形式は変えていません。

- **合意したこと**: 同じ処理基盤に規約集合を渡す。厳密モードは未決の裁定に当たったら止める検証用。プレイ用は未決の裁定を事前に定めた続行規約で処理する。既存の承認済み利用者指定は両モード
  共通の基礎集合に含める。情報漏れ・状態破損・不正入力・実装不足・計算上限はプレイ用でも無視しない。続行規約は対戦全体を終端にする項目から整える。
- **過去の検討案**: 9 章の STRICT-A は厳密モードの定義として採用しません。STRICT-B は合意済みの定義に置きかえました（9 章・11 章の本文は分類の時点の記録として残す）。
- **台帳の変更**（作成スクリプトを直して作り直した。JSON は手で直していない）:
  - `mode_agreements`・`mode_definitions`（合意済みの定義。STRICT-A・STRICT-B は `strict_options_at_classification`・`history`）・`baseline_categories`・`decision_status` を加えた。
  - `conventions` の 18 件に、基礎集合の区分（利用者指定 12・エンジンの簡略化 2・実装上の仮定 3・データの訂正 1）・対象・効果・影響する判定・含まない場面・承認の記録・登録の記録の
    場所を加えた。利用者指定の 12 件だけを `user_agreed`（合意 AGR-MODE-BASELINE-USER）にし、ほかの 6 件は `decision_required` のまま（18 件を一括で承認済みにしていない）。
  - 誤りの訂正: 簡略ルールの 4 対象の `user_ids` に 2 つの ID を両方書いていたのを、登録と同じ 1 つずつに直した。ナッシーの名前・PR1-069 の名前は判定に影響する（`display_only: false`）。
  - 判断事項を 8 つ加え、5 つ（DEC-RULESET-IDENTITY ほか）の置き場所を ruleset-mode-decisions.md に移した（stop-policy-decisions.md には分類の時点の案を履歴として残す）。
  - `--check` に、合意・規約・判断事項の置き場所・設計文書の生成した表の確かめを加えた（16 章）。
- **変えていないこと**: 停止コード・事例・問題の項目（v0.138 の 2 件の修正と、`PSP-INCREASE-ENTRY-PW3-ORACLE`・`PSP-COCOON-DV2-ORACLE` の未修正・`PSP-DECK-CONTENT-PRECHECKS` の残りの
  未確認を含む）・族・族の候補・安全境界。個々の続行規約は 1 つも採っていません。

## 8. プレイ用の規約だけでは解消できない項目

対応群 3・4・5 を含むコードは 110 件です。規約を決めても、実装・計算の改善・保護がなければ続けられません。

| 区分 | 件数 | 理由 |
|---|---:|---|
| PF-COPY-TRANSFORM | 34 | 写したワザ・特殊能力の処理が型ごとに要る（UNSUPPORTED_COPIED_ATTACK などの実装の不足が先） |
| PF-HISTORY-LASTING | 20 | 一部は前の番の記録の不足（旧状態） |
| PF-REACTION-DURING-PROCESS | 10 | 使えると決めた場合の反応の継続 |
| PF-HIDDEN-INFORMATION | 8 | 規約で止めを外しても、秘密への非依存を確かめ直す必要（v0.135・v0.136 の保守的な止め方） |
| PF-RUNTIME-CONTINUATION | 15 | 決定・反応の継続の状態がない |
| PF-RUNTIME-COPY-GAPS | 5 | 実装の不足 |
| PF-RUNTIME-SEARCH-LIMIT | 6 | 上限の超過。枝を削らない計算の改善が要る |
| PF-RUNTIME-DATA | 5 | 図鑑番号・身長・旧形式の記録・デッキリストの不足（推測で埋めない） |
| PF-RUNTIME-REGISTRY | 7 | 未登録・不正な登録のガード（両モードで拒否） |

コード以外の問題（棚卸しの項目）では、次のものが規約だけでは解消できません。

- `GAP-ANSWER-SEARCH-FAIL-OPEN`（256 件の代替回答探索の fail-open）
- `GAP-DEFERRED-HALT-NO-RESUME`（途中停止の再開の操作がない）
- `GAP-SLOWKING-DECLINE-OVERREJECTION`（先読みの止めすぎ）
- `GAP-PRESENT-CORRELATED-OUTCOMES`
- `GAP-UNTIL-TAILS-RESOURCE-BOUND`
- `GAP-QUIZ-REFERENCE-DATA`（図鑑番号のない 225 枚）
- `LIMIT:*` の 7 件
- 新しい漏れの 3 項目

## 9. モードの定義の選択肢（分類の時点。2026-11-03 に合意で置きかえた）

> **経過**: この章は分類の時点（基点 `3e25ac5`）の記録です。2026-11-03 に、厳密モードは「未決の裁定に当たったら停止する検証用モード」、既存の承認済み利用者指定は両モード共通の基礎集合に
> 含める、と合意しました（7.6 節）。STRICT-A は厳密モードの定義として採用しません。下の表の「18 件」のうち、利用者指定ではない 6 件（簡略化 2・仮定 3・データの訂正 1）の扱いは未決です
> （DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS）。

分類の時点では、「厳密モード」の意味は決まっていませんでした（DEC-STRICT-DEFINITION）。

| 案 | 内容 | 既存の採用済みの規約（18 件）の扱い |
|---|---|---|
| STRICT-A（公式の根拠だけ） | 2000.02.14 版の公式ルールと既存の公式資料（最新の説明・エラッタ・裁定）だけを使い、ほかで決めている処理も止める | 利用者指定 12 件（USER-ID は 9 つ。サドン・デスの所有者の戻しを含む）、エンジンの簡略化 2 件、実装上の仮定 3 件、データの修正 1 件が、止める候補になる。たとえば誕生日・発話の省略、公式図鑑の参照、交換の所有権、ちえくらべ、ひかるバンギラスの 2 ワザ、ナッシーの名前、エネルギードレインの v0.68 の採用の仕様（2002 年の Q&A が根拠で、2000.02.14 版の裁定ではない）がこれに当たる |
| STRICT-B（固定したルールセット） | 公式の根拠に、承認済みの利用者指定・記録済みの簡略化・仮定を加えた、版で固定したルールセットに厳密にしたがう | 今のまま（今のエンジンの挙動は STRICT-B に当たる） |

今回、どの規約も無効化していません。公式扱いにもしていません。台帳の `conventions` では、すべてを `decision_required` にしました。

プレイ用モードは、厳密モードのルールセットに、項目ごとに承認したプレイ用の規約を加えるものとして整理しました。すべての停止をなくすことは目的にしていません。

## 10. 両モードで維持する安全境界

内部ガードを、独立した未裁定として数えていません。ガードの存在を不具合の証明にもしていません。棚卸しの `GUARD:*` の ID は台帳の安全境界から引けます。

| 境界 | 内容 |
|---|---|
| SB-NO-SILENT-SKIP | 未対応・未裁定を効果がないものとして処理しない。内部例外を一括で捕まえて効果なしで続ける案は採らない |
| SB-REJECTION-PURITY | 拒否は状態・乱数・ログを変えない。拒否・途中停止・HALTED を区別する |
| SB-SECRET-INDEPENDENCE | 受理・拒否・コード・理由の文・候補が、見えない情報に依存しない（7 章の 3 項目はこの境界の違反・候補） |
| SB-STATE-INTEGRITY | カードの保存則・場の形などの不変条件（StateIntegrityError 3 箇所。うち `engine.py:445` は v0.134） |
| SB-ENGINE-BUG-GUARDS | 「エンジンの不具合」の RuntimeError・NotImplementedError・UnsupportedByKernel 599 箇所。合法な操作の列で起きたら最小の再現を付けて A に再分類する |
| SB-INPUT-VALIDATION | 不正な入力・デッキの検査（IllegalActionError・DeckValidationError。ルール上の不正で、方針の対象ではない） |
| SB-RECORD-REPLAY | 保存・ログ・観測に再現の情報を残す。旧形式の不足を推測で埋めない |
| SB-NO-FAIL-OPEN-SEARCH | 探索の上限で、未探索の枝を安全とみなさない |

## 11. モード導入に向けた設計メモ（実装していない）

> **経過**: この章は分類の時点の設計メモです。合意（7.6 節）を受けた設計は [ruleset-mode-design.md](ruleset-mode-design.md) にあります（識別の照合値・事例単位の採用・構成の検査・
> 旧保存状態は作成した版が分かる場合だけ対応付ける、などを加えた）。下の例（`ruleset = {...}`）は案のままです。

1. **規約の集合をモードと別に識別する。**
   - モード名（strict・play）だけで挙動を決めず、採る規約の集合に ID と版を付ける（例: `ruleset = {base: "2000-02-14", conventions: [USER-…, PLAY-…], version}`）。
   - モードは「集合に入っていない処理に当たったら止める」という共通の動作のまま、どの規約を集合に入れるかで差を作る。
   - 規約の処理は、今の利用者指定と同じく登録の記録（`effects.USER_SPECIFIED_RULES` など）に置く。`engine.py`・`resolution/` にモード名・カード ID の分岐を加えない。
   - 例外コードを一律に無視する実装はしない。
2. **対戦の開始時に固定する。**
   - `new_game` の入力で規約の集合を受け取り、状態に持つ。途中の変更は、既定では受け付けない（DEC-MODE-CHANGE-DURING-GAME）。
   - サドン・デスの延長戦の区間は同じ集合を引き継ぐ（`SEGMENT_FIELD_POLICY` の keep に加える）。
3. **保存・ログ・再生・比較で識別する。**
   - 書き出しの形式を上げ、規約の集合の ID と版を保存に入れる。ログの `game_created` にも書く。
   - lockstep・前の版の組の比べは、同じ集合どうしでだけ比べる。違う集合の比べは「意図した差」の一覧として出す。
4. **厳密とプレイ用で違う結果を監査する。**
   - 同じ seed・同じ操作で 2 つの集合を走らせ、違いが出た最初の段を記録する道具（lockstep の拡張）を作る。
   - 違いは、規約の ID が理由のログを伴う場合だけ許す。
   - twin の比較（秘密への非依存）は、どちらの集合でも走らせる。
5. **既存の利用者指定の記録と対応させる。**
   - USER-ID 9 つ（`USER_SUDDEN_DEATH_OWNERSHIP_RESET` を含む）・簡略化・仮定・データの修正を、規約の集合の要素として列挙する。ほかのカードへの適用範囲は、記録の範囲のまま変えない。
   - プレイ用の規約も同じ形（ID・日付・範囲・原文との差・研究の論点を解決済みにしないこと）で記録する。
6. **旧保存状態に方針の情報がない場合を決める。**
   - 既定案は、その版の挙動（STRICT-B 相当の、その時点の採用済みの集合）として読む。推測で別の集合を当てはめない（DEC-LEGACY-STATES）。
   - 集合の ID が分からない値なら拒否する。

## 12. 推奨の順序（案）

1. 新しい漏れ（7 章）の修正の判断（DEC-INFO-LEAK-FIXES）。モードの導入より前に、両モード共通の不具合として扱う。
2. 厳密モードの定義（DEC-STRICT-DEFINITION）と、規約の集合の識別（DEC-RULESET-IDENTITY）。ここが決まらないと、既存の利用者指定の扱いが決まらない。
3. 対戦を止める項目の規約: 切り直しの補償（DEC-MULLIGAN-COMPENSATION。通常のデッキでも準備が止まる）、両側ねむり（DEC-SLEEP-COIN-ORDER）、途中停止の再開（DEC-DEFERRED-RESUME）。
4. 頻度の高い拒否の族（PF-DAMAGE-SCOPE・PF-KNOCKOUT-TIMING・PF-HIDDEN-INFORMATION）。規約の影響が広いので、道具の対戦で差を測る計画を先に固定する。
5. 規約だけで済む族（PF-USE-WITHOUT-EFFECT・PF-UP-TO-ZERO・PF-STATED-COUNT-SHORT など）を、コードごとに判断する。
6. 実装・計算の改善が要るもの（8 章）は、モードと別の作業単位にする（棚卸しの修正計画 R3・R4・R6・R7・R8・R9）。

## 13. 検証

| 検証 | 結果 |
|---|---|
| 全定義・参照と台帳の突き合わせ | `--check`: エンジンのコード（リテラル・コメント）と、台帳の研究コード・表外コードの集合が一致（`UNSUPPORTED_COMMANDS` は型の組の名前でコードではないので除く） |
| 台帳の ID の一意性・参照切れ | `--check`: 重複なし。事例・親・族・判断事項・棚卸しの参照がすべてある |
| 研究コードと表外コードの区別 | `--check`: 研究コードの集合が `research_links.json` の `stop_codes`（316）と一致し、表外コードと重ならない |
| 方針未決の項目に承認済みの挙動が入っていないこと | `--check`: 方針の状態は unconsidered・proposal・decision_required だけ。判断事項のある項目は decision_required。既存の規約はすべて decision_required |
| 修正済みの問題を現行の未修正として数えていないこと | 修正済みは問題の項目だけ（停止コードを fixed にしない）。修正済み 5 件（クイズ 3・カードめくりゲーム・サドン・デス）は現在有効の集計に入れていない |
| 根拠なしに到達不能とした項目がないこと | `--check`: 到達可能性は 5 つの軸だけ。legal_sequence・constructed_board には証拠がある |
| 作り直しとの一致 | `--check`: 現行コードと証拠から作り直した台帳が、書き出した台帳と同じ |
| エンジン・既存テスト・データの動作を変えていないこと | 変更は文書 3 つと、読むだけの 2 つのスクリプト、`--check` を呼ぶテスト 1 つ（16 章）。kyuura_engine・既存のテスト・データは変えていない |

全体の対戦テスト・全体のテストは再実行していません（文書と読むだけのスクリプトの変更のため）。16 章の範囲を実行しました。

## 14. 未確認事項と限界

- 到達可能性の `constructed_board` の多くは、テストの表明らしい行の静的な分類です。行の実行・盤面の作り方・隣の受理枝は、個別に確かめていません。
- 動的に HALTED に変わる経路（`error.code` を渡す変換）は、コードごとには特定していません。
- 研究の論点（316 件）の公式資料を再調査していません。kyuura の固定コミットより後の記録も照合していません（棚卸しの `RESEARCH-ALIGNMENT-NOT-LATEST`）。
- 事例の分割は、発生条件の違いを確かめた 7 コードだけです。ほかのコードは単一の事例として扱い、分割の要否は未確認です。
- 漏れの横断は、使う前の確かめのうち山札・サイドを読むものだけです。答えの候補・理由の文・決定の中の拒否の全件は見ていません。
- 道具の対戦の証拠は、v0.134〜v0.136 の検証で保存したもの（リポジトリの外）だけです。それより前の版の正式な対戦の報告からは、MG1 だけを拾いました。
- 600 の内部ガード・756 の None を返す候補の意味と到達性は、棚卸しのまま未確認です。

## 15. 付録 A: 比較プローブ（エンジンは変えない）

スクリプトと出力は `C:/dev/kyuura-engine-verification/stop-policy/`（リポジトリの外。`MANIFEST.md` に sha256。同じ木での再実行で出力がバイト単位で同じ）。どちらも `tests/helpers.build_test_state` で盤面を作り、`tests/log_audit.twin_command_problems` で、プレイヤー 0 から見て公開の情報が同じ 2 盤面に同じコマンドを送りました。

- ST1:
  - 手札にエネルギー転送（PMCG3-044）。
  - 山札は基本エネルギーでないカード 11 枚に、炎エネルギー 1 枚かミニリュウ 1 枚。
  - サイドは、ミニリュウ 1 枚か炎エネルギー 1 枚と、スリープ 5 枚（山札と入れかえる）。
  - 結果: `[('accepted',), ('UnsupportedError', 'UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET')]`
- FC1:
  - 手札にエネルギーアーク（neo2-053）。
  - 山札の基本エネルギーは 2 枚か 1 枚で、もう 1 枚はサイド。
  - 結果: `[('accepted',), ('UnsupportedError', 'UNRESOLVED_STATED_CARDS_SHORT')]`

## 16. 追加したスクリプト・テスト

- `scripts/stop_policy_scan.py`: 静的な抽出（読むだけ）。
- `scripts/build_stop_policy_classification.py`: 台帳を作る（`--write`）・確かめる（`--check`）。
  - 族・事例・規約・判断事項・安全境界の定義はこのスクリプトにある。
  - 道具の証拠（リポジトリの外）がない環境では、作り直した台帳との比べを省き、不変条件だけを確かめる。
- `tests/test_stop_policy_classification.py`: `--check` の不変条件（コードの集合の一致・ID・参照・方針の状態・到達可能性の証拠）を確かめる。分類の件数は写していない。
- 2026-11-03 の追加（7.6 節）: `--check` は、合意の出典（利用者の指示で、公式・kyuura の解決として記録しない）、規約の状態（`user_agreed` は利用者指定で、承認の文が根拠の文書にあるもの
  だけ）、利用者指定の登録の記録（`effects.USER_SIMPLIFICATIONS` など）の対象の鍵と規則の ID が台帳と同じこと・登録の対象がすべて台帳にあること、名前の扱いを表示だけにしないこと、
  判断事項の見出しが置き場所の文書にちょうど 1 つあること、ruleset-mode-design.md の生成した表が台帳と同じことを確かめる。`--write` はその表も書く。テストは、それぞれの確かめが
  壊した台帳を見つけることを確かめる。
