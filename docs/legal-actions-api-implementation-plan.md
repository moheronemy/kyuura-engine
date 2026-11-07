# 合法手 API（U7）の実装計画

[legal-actions-api-design.md](legal-actions-api-design.md) の実装の順序と完了の基準です。U7-1 は v0.160 で実装しました（[legal-actions-u7-1.md](legal-actions-u7-1.md)）。ほかの単位は計画だけです。単位の表は `scripts/build_legal_actions_api_design.py` の `SPEC` から作ります（`--check` が依存の順・回帰テスト・完了の基準の有無を確かめる）。

## 1. 識別の方式との依存

- U7 の初版は、候補をホストの中で今の状態と今の実装から作り、保存して別の実装で使いません。したがって、新しい識別の方式（[implementation-identity-design.md](implementation-identity-design.md) の M3〜M6）の実装を待たずに始められます
- U7-1 で `kyuura_engine/legal_actions.py`（名前は実装のときに決める）を加えると、識別の設計の `--check` がファイルの分類の漏れとして失敗します。そのファイルを部品 `legal_actions`（層 `api_format`）に分類し、ゲームの挙動のファイルがそれを読み込まないこと（依存の向き）を同じ `--check` で確かめます
- 今の識別の方式（`kyuura-package-files-sha256/1`）では、新しいファイルは `behavior_digest` に入ります（INSTRUMENTATION_FILES の外）。U7 の実装のリリースでは、いつもどおり前の記録は unsupported になります（今の判定を変えない）。識別の移行の M5 のあとは、U7 のファイルの変更は U4・スナップショットの記録を拒む理由になりません
- 候補の応答の保存・別の実装での読み取りは対応しません。対応するなら、応答の形式の版と `legal_actions` の部品の一致を求める判定を、識別の方式の機能の表に加えます

## 2. 単位

<!-- generated:units begin -->
| 単位 | 状態 | 名前 | 依存 | 範囲 | 回帰テスト | 完了の基準 |
|---|---|---|---|---|---|---|
| `U7-1` | implemented | 枠組みと決定への回答（最初の縦の単位） | なし | 応答の形式・取っ手（game・revision）・ホストの認証の境界・古い取っ手の拒否<br>決定への回答（ResolveDecision・TakePrize・PromoteActive）を observe の decision から作る（complete）<br>番を終える（EndTurn）<br>番でない・終局・停止は空の候補（complete） | T-TWIN-RESPONSE（決定）<br>T-STARTED-SEARCH<br>T-NO-SIDE-EFFECT<br>T-OTHER-ACTOR<br>T-STALE<br>T-NO-VERIFIER<br>候補どおりに送った回答を apply_command が受理する（既存の対戦の決定で） | 決定待ちのすべての種類（OPTION_MEANINGS の語彙）で候補ができ、漏れの回帰テストが通る。実装の識別の分類に legal_actions のファイルを加え、識別の設計の --check が通る |
| `U7-2` | planned | 準備とホストの操作 | U7-1 | PlaceStartingPokemon（たねポケモンの手札から。段: バトル場 → ベンチ）<br>DrawMulliganCards<br>ReportJankenResult・StartSuddenDeath（ホストの操作主体だけ） | T-TWIN-RESPONSE（準備）<br>準備の候補から作った操作で、固定デッキの対戦が始まる | 準備の段階が complete |
| `U7-3` | planned | 通常の操作（ワザ・トレーナー・パワーの外） | U7-2 | PlayBasicToBench・AttachEnergy・EvolvePokemon・Retreat（費用は条件で表す） | T-TWIN-RESPONSE（通常の操作）<br>T-NOT-HIDDEN | これらの種類について、本人の知識だけで決まる確かめを候補の作成に使う。scope に含めた種類を示し、main は partial |
| `U7-4` | planned | ワザ | U7-3 | UseAttack（ワザ → 任意の指定。対象は受理のあとの決定）<br>宣言の前の確かめのうち、本人の知識だけで決まるもの（v0.147〜v0.151 の持ち主の知識の関数）を processability に使う | T-TWIN-RESPONSE（v0.147〜v0.151 の双子の盤面）<br>T-TWIN-REFINE<br>T-NOT-HIDDEN（未裁定のワザ） | ワザの候補で、先読みを呼ばない。決められないものは unverified |
| `U7-5` | planned | トレーナー・パワー・スタジアムとその他 | U7-4 | PlayTrainer・UsePokemonPower・UseStadium・RemoveDisguise・DiscardFromPlay・RevealFaceDown・CheckFaceUpDeckCard<br>入力はカードの登録が宣言する（共通の処理にカード ID の分岐を加えない） | T-TWIN-RESPONSE（トレーナー・パワー）<br>登録のないカードは unverified（消さない） | すべてのコマンドの型に候補の種類がある。main が complete と称せるかは D-U7-COMPLETENESS |
| `U7-6` | planned | GUI・ルールベースの AI への接続 | U7-1 | API だけを使う方策（内部の状態・秘密の配分を読まない）<br>GUI の表示（processability ごとの表示）<br>既存の方策（tests/helpers の trainer_policy_command など）は内部の状態を読むので、公開の API に流用しない | API だけを使う方策で固定デッキの対戦が終局・停止まで進む<br>方策が受け取る値が応答だけであること | 決定・準備は U7-1・U7-2 のあとに接続できる。通常の操作は単位ごとに広げる |
<!-- generated:units end -->

最初に作る縦の小さな単位は **U7-1** です。応答の形式・取っ手・ホストの認証の境界・古い取っ手の拒否という枠組みを、決定への回答（既存の `observe` の `decision` をそのまま使えるので、新しい確かめを作らずに完全な候補にできる）と番を終える操作で通します。漏れの回帰テストの枠組み（双子の応答の比べ）もここで作り、あとの単位はテストの盤面を足すだけにします。

広げる順序: U7-1（決定・番を終える）→ U7-2（準備とホストの操作）→ U7-3（通常の操作）→ U7-4（ワザ）→ U7-5（トレーナー・パワー・その他）。GUI・ルールベースの AI への接続（U7-6）は U7-1 のあとに始め、単位ごとに使える操作を広げます。

## 3. 情報漏れの回帰テスト

- 双子の盤面: v0.135〜v0.151 のテストの双子（`tests/log_audit.twin_command_problems` の前提。v0.137 の `owner_knowledge`）を再利用し、応答の比べ（候補・数・並び・理由・入力の制約・完全性）を加える。重い対戦は使わない
- 山札の検索: 始まる前は同じ、始まったあとの決定の選択肢だけは違ってよい（T-STARTED-SEARCH）
- 不正な問い合わせ: 知らない候補・見えないカード・範囲の外の数への答えが双子で同じ（T-TWIN-REFINE）
- 副作用: 何度取っても状態・乱数・ログ・決定の通し番号が同じ（T-NO-SIDE-EFFECT）
- 検証者用の値: 閲覧用記録の入ってはいけない項目（`view_record.FORBIDDEN_KEYS`）と同じ名前が応答にないこと（T-NO-VERIFIER）

## 4. GUI・ルールベースの AI への接続

- 方策は API の応答（と自分の観測）だけを受け取る。内部の状態・秘密の配分を読まない。既存の方策（`tests/helpers.trainer_policy_command` など）は内部の状態を読むので、公開の API に流用しない
- GUI は processability ごとに表示する（実行できない区分も表示し、ゲーム上の禁止と区別する）
- `unverified`・`may_stop_later` の候補を選ぶかは方策の判断。送った結果は `submit` の結果（U2）で受け取る

## 5. 区別

- 採用済み: 設計の文書 1 章の `採用済み` の原則（ADOPT-U7-PRINCIPLES）
- 推奨案: この計画の単位・順序・完了の基準と、設計の文書の表の値
- 利用者の判断が要る: 設計の文書 9 章（D-U7-*）と、識別の設計の判断事項のうち U7 にかかわるもの（D-VERSION-AUX は U7 の初版には要らない）
