# U7 の総合検証の計画（実行していない）

合法手 API（U7-1〜U7-5g）と、それを使う GUI（kyuura-engine-gui）の総合検証の計画です。この文書は調査と計画だけで、テスト・ビルド・対戦の探索・総合検証は始めていません（10 章）。エンジン・GUI・renderer のコードと依存は変えていません。

## 0. 要約

- 検証の対象は、エンジン `e26df79`（0.172.0）・GUI `b1037bc`・renderer `af88231` の組です（1 章）。エンジンの `05a6749` は検証の結果を書いた文書だけのコミットで、参照する文書の版として別に記録します
- 目的を 6 つに分けます（2 章）。「全種類に候補がある」「全入力経路を扱える」「全効果が完走する」は別の主張で、U7-5 の単位が implemented でも R-2〜R-5・PT-5e・UP-5t の残りは解消していません
- 段階は低負荷のものから 11 段（4 章）。必須の回帰（E0〜E5・G0〜G5）と、費用の大きい追加（X1〜X4）を分けます（6 章）
- 重い処理は並列にせず、テストは 1 モジュール（GUI は 1 ファイル）ずつ別のプロセスで実行します。資源不足で止まったら、自動では重い再実行をしません（7 章）
- 証跡の恒久の保存先は `C:/dev/kyuura-engine-verification-u7/` です（8 章）
- 前回のクリーンな場所では、GUI の e2e・preview を実行していません。b1037bc で直したのに実行していない e2e が 4 ファイルあります（turn-basics・u75e・u75・attacks）。これを GUI 側の出発点にします（5.2 節）

## 1. 検証の対象と参照した資料

### 1.1 固定する対象（コードの検証対象）

| 対象 | コミット | 版・固定 | 確かめた場所（2026-11-08。読み取りだけ） |
|---|---|---|---|
| エンジン | `e26df79cc6dec913c1d15b5d8203df066334d65d` | 0.172.0 | 公開ブランチ `origin/claude/u7-5fg-impl` にある。`origin/main`（`88ad4d9`）は含まない |
| GUI | `b1037bc6651a4a7104a0f1203e73667fac961d33` | `server/requirements.txt` がエンジン `e26df79` を Git の URL で固定。`web/package.json`・`package-lock.json` が renderer `af88231` を固定 | 公開ブランチ `origin/feature/engine-u7-5fg` にある。`origin/main`（`088822c`）は含まない |
| renderer | `af882310059c7f33bc371d31b859b09f5428f6d1` | GUI の依存（`github:moheronemy/kyuura-card-renderer#af88231…`） | `origin/main` の祖先。main の先頭は `7f9d9b6`（af88231 のあとのマージ）だが、検証の対象は af88231 のまま |

- 参照する文書のコミット: エンジン `05a6749`（`e26df79` との差は `docs/implementation-status.md`・`docs/legal-actions-u7-5fg.md` だけ）と、この計画のブランチ `claude/u7-integration-plan`。GUI の文書は `b1037bc` の `README.md`・`docs/engine-contract.md`
- main の先頭・公開ブランチは変わりうるので、実行の前に上のコミットが同じであることを確かめ、違っても別のコードへ移らない（E0・G0）
- 比べる基点（共有エンジンの回帰）: U7 の前の最後のコミット `a2c51a1`（v0.159 の証拠の記録。`eb73191` の全体のテストのあとで、`kyuura_engine/` は同じ）。U7 の最初の仕様は `174e87e`、U7-1 の実装は `6b0495d`

### 1.2 作業の場所（2026-11-08 の状態）

| 場所 | 状態 | 扱い |
|---|---|---|
| `C:\dev\kyuura-engine` | main `0c00b56`・未コミットの変更 0 | 触れない |
| `C:\dev\kyuura-engine-v149` | `claude/u7-5fg-impl` `05a6749`・変更 0 | 実行の木には使わない（新しい木を作る。4 章 E0） |
| `C:\dev\kyuura-engine-u7plan` | この計画のブランチ | 文書だけ |
| `C:\dev\kyuura-engine-gui` | `feature/local-gui-v0.164`・利用者の未コミットの変更 13 件 | 触れない |
| `C:\dev\kyuura-engine-gui-wt-u75fg` | `feature/engine-u7-5fg` `b1037bc`・変更 0 | GUI の作業場所の検証に使える（G0 で状態を確かめる） |
| `C:\dev\kyuura-card-renderer` | main `7f9d9b6`・変更 0 | 読むだけ |

### 1.3 確かめた資料

- エンジン: `docs/legal-actions-u7-1.md`〜`u7-4.md`・`u7-5ab.md`・`u7-5c.md`・`u7-5d.md`・`u7-5e.md`・`u7-5fg.md`（6.2 節の限定の検証・8 章）・`legal-actions-u7-5-design.md`（F 表・PT-5e・UP-5t）・`legal-actions-u7-5-implementation-plan.md`・`legal-actions-u7-5fg-spec.md`・`legal-actions-api-implementation-plan.md`・`legal-actions-decision-audit.md`・`chaos-gym-borrow-t-f1.md`（6 章の差）・`testing.md`・`integration-verification-v0.159.md`（U1〜U6 の総合検証）・`play-set-verification-v0.146.md`（108 バッチの扱い・メモリ不足の記録）・`installation.md`
- エンジンのコード（読むだけ）: `kyuura_engine/legal_actions.py` の `RESIDUAL_CLASSES`（1948〜1962 行）・`_residual_present`（1968 行）・`_unverified_paths`（1984 行）・`_candidates` の completeness（559〜587 行）・PT-5e の集合（1451 行）、`tools/engine_lockstep.py`・`tools/snapshot_audit.py`・`tools/existing_effect_games.py`・`tools/stress_engine.py`・`tools/test_runner.py` の引数、`scripts/check_distribution.py`・`scripts/smoke_installed_package.py`・生成器の `--check`
- テスト: U7 の 18 モジュールと直接関係するモジュール（3 章の表）。`tests/test_*.py` は 303 モジュール（静的な数え上げ。v0.159 の全体のテストは 283）
- GUI（`b1037bc`。読むだけ）: `README.md`・`docs/engine-contract.md`（9〜13 章、13.3.1・13.8）・`web/src/state/checkGate.ts`・`useEndpointSession.ts`（`generation`・`checkEpoch`）・`web/e2e/*.spec.ts`・`helpers.ts`・`playwright.config.ts`・`scripts/setup.mjs`・`server/tests/*.py`・`server/kyuura_gui_server/app.py`（`/api/health`）・`engine_source.py`・`scenarios.py`

### 1.4 資料の食い違い（この計画では直していない）

| 箇所 | 内容 | 扱い |
|---|---|---|
| GUI `docs/engine-contract.md` 13.8（431 行） | `attachToActive` を使うのは u75・u75e としているが、`attacks.spec.ts` も 5 か所（33・68・92・97・136 行）で使う。attacks も b1037bc の変更のあと実行していない | G1 の対象に attacks を入れる。GUI の文書の訂正は GUI の別の作業 |
| GUI `README.md` 341 行 | local-flow の 3 つの固定例（決定待ち・停止・サドン・デス）を「再生した盤面」と書くが、停止（`halt`）は `ClientHub.start` で始める（`scenarios.py` 69・116〜119 行） | 5.3 節の区分はコードに合わせる。文書の訂正は GUI の別の作業 |
| エンジン `docs/legal-actions-api-implementation-plan.md` 3・21 行 | 「ほかの単位は計画だけ」「U7-5 planned」のまま（U7-5 は v0.168〜v0.172 で実装済み） | 総合検証の結果の文書で訂正する（この計画では変えない） |
| GUI 13.8 の「JUnit に残した」 | `playwright.config.ts` の reporter は list だけ。前回・今回はコマンド行で `--reporter=list,junit` を指定した | G 段のコマンドに reporter を明記する（5.2 節） |

## 2. 検証の目的

| 番号 | 目的 | 主張の形 | 主に使う段 |
|---|---|---|---|
| P1 | U7 を通した操作と直接のコマンドの挙動の一致 | 候補 → inputs → check → submit で送ったコマンドの結果（outcome・状態・乱数・ログ・決定・観測）が、同じコマンドを `apply_command`（アダプタの `submit`）へ直接送った結果と同じ | E1・E3・X1 |
| P2 | 候補・入力・check が副作用を持たず、秘密を漏らさない | candidates・inputs・check の前後で状態・乱数・ログ・決定の番号が同じ。情報境界の双子で、相手・観戦者の応答・観測・ログ・更新が同じ | E1・E3・X1 |
| P3 | 主体・取っ手・遅れた応答・拒否の配信の境界 | 取っ手（game・revision・candidate）の失効、主体の違い（`CANDIDATES_WRONG_ACTOR`）、refused と rejected の区別、拒否が相手・観戦者の更新を作らないこと。GUI では遅れた応答を今の画面に使わないこと | E1・G1〜G3 |
| P4 | GUI からの代表的な操作と状態の更新 | 実エンジンに対する画面の操作で、受理・拒否・受理のあとの決定・停止・終局の表示と、観測の更新が合う | G1〜G4 |
| P5 | coverage・residual・処理可能性の表示の正確さ | エンジンの応答（completeness・`partial_residual`・`residual.present` の public／actor・`unverified_paths`）と、GUI の表示の区分が合う。complete を「全部の操作が完走する」と表示しない | E1・G2・G3 |
| P6 | 通常のインストールと配布物での再現 | Git の URL からの通常のインストール・wheel と sdist・クリーンな場所で、同じ版・同じ実装の識別で同じ結果 | E5・G4・G5 |

区別する 3 つの主張（どれも U7-5 の implemented からは出ない）:

| 主張 | 今の根拠 | 解消していないもの |
|---|---|---|
| 全種類に候補がある（種類の網羅） | 番のプレイヤーの MAIN の `not_covered_kinds` は空（v0.172） | `check_face_up_deck` は表示だけ（`display_only_kinds`）。番のプレイヤーの MAIN のほか（R-4）は API の範囲外 |
| 全入力経路を扱える（経路の網羅） | なし。MAIN は `partial_residual: ["R-2"]` で partial のまま | R-2（うらのバトル場のワザといっしょに選ぶもの）・R-3（自分のうらのカードの特殊能力のうち入力を返さない型）・R-5（入力を返さない候補） |
| 全効果が完走する（受理と完走） | なし。complete は「候補の取得が網羅している」だけ（`legal-actions-u7-5fg.md` 2.3 節） | `unverified_paths`（受理の分からない経路）、PT-5e（山札から引いて試すトレーナー 5 つ。`use_condition_not_evaluated`）、UP-5t（名前で解決できない呼び出しの先）、受理のあとの停止 |

この検証で「完走する」を示すことはできません。各段の合格は、その段の主張の範囲だけを言います。

## 3. 既存のテストと、新たな確かめの対応

件数は網羅の根拠にしません。行は主張ごとで、「既存」はそのテストが何を比べるかを読んで判断したもの（コードを読んだ判断）です。

### 3.1 エンジン

| 主張 | 既存のテストで確かめているもの | 足りないもの（新たな確かめ） |
|---|---|---|
| 3 規約集合での一致（P1） | `test_legal_actions_u7_1`〜`u7_5e`・`u7_5g_energy2`・`test_client_api`・`test_chaos_gym_borrow_t_f1`・`test_legal_actions_decision_audit` は `SETS=(None, S2A, PO)` で、構築盤面・補助関数・new_game からの合法な列を分けて比べる | `u7_5f`・`u7_5g_residual`・`u7_5g_face_down_power` は 3 集合を回さない。どれも固定の少数の盤面で、U7 だけで長い対戦を進めて直接と比べる道具はない（tools・scripts に legal_actions を使う対戦の道具はない）→ X1 |
| 候補・inputs・check が状態・乱数・ログを変えない（P2） | `snap()`（u7_1 52 行）を前後で比べるテストが u7_1〜u7_5g_energy2・face_down_power・client_api・decision_audit・T-F1 にある | 固定の盤面だけ。対戦の各歩で確かめたことはない → X1 |
| 情報境界の双子（P2） | u7_1〜u7_5e・5f・5g_residual・face_down_power・decision_audit・T-F1 に双子がある（本人の知識と公開の情報を同じにし、本当のカード・山札の並びなどの秘密の配分だけを変える） | 双子の作り方の確かめ（公開の観測が同じであることを先に確かめているか）をモジュールごとに読む。公開の情報の違う別の対戦は双子と呼ばない → E1 の読む確認・X1 |
| refused・rejected・accepted のあとの決定・停止・終局の区別（P3） | u7_3・u7_4・u7_5ab・u7_5c・u7_5e・client_api は 3 つとも。u7_5d は refused・accepted、u7_5f は refused だけ | 受理のあとの停止・終局まで U7 で進めた対戦はテストの固定の場面だけ → X1 |
| 拒否が相手・観戦者の更新を作らない（P3） | u7_3〜u7_5e・face_down_power・client_api・T-F1（client_api で他者の更新なし） | u7_5f・u7_5g_residual は観戦者だけ |
| 保存・復元・記録・再実行・閲覧用記録（P1・P6） | u7_1（復元で取っ手が失効）・u7_5c・u7_5d・u7_5e・T-F1（完全な記録・U4 の再実行・閲覧用記録）。`test_replay_record_v0_153`・`test_replay_run_v0_154`・`test_view_record_v0_155`・`test_state_snapshot_v0_157`・`test_snapshot_replay_v0_158`・`test_integration_u1_u6_v0_159` | U7 の各操作の場面での保存・復元の網羅 → E4（`tools/snapshot_audit.py` を U7 のモジュールに 1 つずつ） |
| energy2・`options_by_path`・不正な経路の拒否 | `u7_5g_energy2`（11。構築盤面・`StageCheckTest`・BLAINE_DECK seed 1 の new_game を 3 集合） | なし（E1 で再実行する） |
| FU2 の表示だけの候補と R-4 の主体・段階 | `u7_5f`（8。フラッシュの合法な列・構築盤面）・`u7_5g_residual` | 準備の段階の R-4 は実エンジンの対戦では届いていない（GUI の 13.6 節）→ X1 で届けば確かめる。届かなければ未確かめのまま |
| 本人のうらの能力の公開範囲・入力を返さない型・受理・拒否・トラッシュ | `u7_5g_face_down_power`（10。マチスの秘策の盤面から apply_command の列・補助関数） | 3 集合を回さない。new_game からの列はない → E1 で再実行。X1 の対象 |
| residual の固定の分類と public／actor の境界・R-2 の残る MAIN の partial | `u7_5g_residual`（9。DocumentTest で文書の表と `RESIDUAL_CLASSES` を照らす） | なし（E1） |
| T-F1／F-8 の意図した差 | `test_chaos_gym_borrow_t_f1`（12）・`test_stadium_reuse_special_energy_v0_58`（期待を 1 か所直した） | 既存の参照データ・lockstep での差の現れ方 → E5 後の X2（lockstep）で、差を 1 局ずつ割り当てる |
| PT-5e・UP-5t の監査の残り | 文書の記録だけ（`legal-actions-u7-5-design.md` 171・185 行、`legal-actions-u7-5e.md` 89・93 行） | 解消は総合検証の範囲の外。E1 では、`unverified_paths` に PT-5e の 5 実装が `use_condition_not_evaluated` で出ることだけを確かめる |
| 共有エンジンの回帰 | 全体のテスト（v0.159 で 283 モジュール） | U7 で `engine.py`・`resolution/flow.py`・`effects.py` の確かめを `check_*` に分けた（「処理は変えない」）。T-F1 だけが挙動を変えた → E3（全体のテスト）・X2（lockstep） |

### 3.2 GUI

| 主張 | 既存の確かめ | 区分 | 足りないもの |
|---|---|---|---|
| attach_energy の送る前の check（1 枚・2 枚） | 単体 `checkGate.test.tsx`（4）・`TurnBasics.test.tsx`・`U75fg.test.tsx`・`AppU75fg.test.tsx`、e2e `u75fg.spec.ts` のカツラ（1 件。作業場所で 1 回） | 模擬の応答と実エンジン | 直したが実行していない e2e 4 ファイル → G1 |
| 上流の変更・2 枚目の解除・元の入力に戻したときの check の無効化 | 単体（模擬）・e2e カツラ（遅らせた check を通信の差し替えで作る） | 模擬と実エンジン | クリーンな場所での e2e → G4 |
| 2 段・3 段の特殊能力 | e2e `u75e.spec.ts`（ロケット団のヒトカゲ・2 段は new_game、エナジートランス・3 段は再生した固定例） | 実エンジン | G1 |
| 本人のうらの能力と閲覧者の切り替え | e2e `u75fg.spec.ts` 136・161 行（new_game からの固定例）、単体 `AppU75fg.test.tsx` | 実エンジンと模擬 | G2 |
| FU2 で check・submit の要求が出ない | e2e `u75fg.spec.ts` 79 行（再生した固定例）・単体 `AppU75fg.test.tsx` | 実エンジンと模擬 | G2 |
| residual と complete／partial の表示 | 単体 `U75fg.test.tsx`（模擬）・e2e フラッシュの R-4 | 主に模擬 | R-2・R-5 の present は模擬だけ（実の場面に届いていない） |
| 拒否の本人だけの表示・受理のあとの決定・停止 | e2e `u75.spec.ts` 錯乱ジム・`attacks.spec.ts` ドライアップ・`local-flow.spec.ts` | 実エンジン | G1・G2 |
| 遅れた応答と古い Canvas の破棄 | 単体 `CardImages.test.tsx`（119〜199 行）・`AppCardImages.test.tsx`・`AppTurnBasics.test.tsx`、e2e `card-images.spec.ts` 89 行・`turn-basics.spec.ts` 148 行・`attacks.spec.ts` 76 行 | 模擬と実 renderer | G1・G2 |
| 開発サーバーと本番ビルドの preview | 前回の作業場所の preview 4 件 | 実エンジン | G3 |
| クリーンな場所 | 前回: setup・接続層 113・単体 221・型検査・ビルドだけ。e2e・preview は未実行 | — | G4（e2e・preview を含める） |

## 4. 段階

各段は前の段の合格を条件に始めます。段の中の対象も 1 つずつ順に実行します。

共通の環境（エンジン）: Windows 11・Python 3.14 系（実行のときの版を記録）・`PYTHONUTF8=1`・`MSYS=noglob`・`PYTHONPATH` は設定しない。git は PowerShell から（msys の引数の展開を避ける）。

共通の環境（GUI）: Node.js・npm・Edge の版を記録。接続層の Python は `server/.venv`（Git の URL からの通常のインストール）。

モジュールごとの実行には、各段の始めに証跡のフォルダへ書く実行の道具（以下「順の道具」）を使います。形は前回の限定の検証で使ったもの（1 モジュールを `python -u -m unittest -v tests.<モジュール>` の 1 プロセスで実行し、開始・終了・終了コード・`Ran N tests`・結果の行・skip の数を JSON Lines に書く）と同じで、道具そのものを証跡に保存し sha256 を記録します。

### E0. 固定と準備（低負荷・テストなし）

- 主張: 対象のコミットと環境が 1.1 節のとおりで、作業の場所が汚れていない
- 対象: エンジン `e26df79`、GUI `b1037bc`、renderer `af88231`
- コマンド（読み取り）:
  - `git fetch origin`・`git rev-parse <コミット>`・`git branch -r --contains <コミット>`（3 つのリポジトリ）
  - エンジンの実行の木を新しく作る: `git worktree add --detach C:\dev\kyuura-engine-u7verify e26df79cc6dec913c1d15b5d8203df066334d65d`
  - 木の指紋（追跡ファイルの数と sha256 の一覧）を前後で取る（v0.159 の `fp.py` と同じ方法。道具は証跡に置く）
  - ツールの版: `python --version`・`git --version`・`node --version`・`npm --version`・Edge の版
  - 動いているプロセスの一覧（python・node・msedge の pid とコマンド行）を記録する（他のセッションのプロセスを見分けるため。止めない）
- 合格: コミットが一致し、木に未コミットの変更がない。違えば止めて報告する（別のコードへ移らない）
- 証跡: `E0/` に commits.json・tools.json・fingerprint_before.json・processes_before.json

### E1. U7 の限定の回帰（必須・低負荷）

- 主張: U7 の各単位のテストと直接関係するテストが、固定の木で通る（P1〜P3・P5 の固定の場面）
- 対象（30 モジュール。1 つずつ）:
  - U7: `test_legal_actions_u7_1`・`u7_2`・`u7_3`・`u7_4`・`u7_5ab`・`u7_5c`・`u7_5d`・`u7_5e`・`u7_5f`・`u7_5g_residual`・`u7_5g_energy2`・`u7_5g_face_down_power`・`test_client_api`・`test_legal_actions_decision_audit`・`test_legal_actions_api_design`・`test_legal_actions_u7_5_design`・`test_legal_actions_u7_5fg_spec`・`test_chaos_gym_borrow_t_f1`
  - 直接関係: `test_distribution`・`test_preset_decks_v0_20`・`test_energy_control_power_suppression_v0_59`・`test_secret_plan_v0_67`・`test_stadium_reuse_special_energy_v0_58`・`test_instant_trainers_v0_55`
  - 記録・保存: `test_replay_record_v0_153`・`test_replay_run_v0_154`・`test_view_record_v0_155`・`test_state_snapshot_v0_157`・`test_snapshot_replay_v0_158`・`test_integration_u1_u6_v0_159`
- コマンド: `python <証跡>/run_seq.py <証跡>/E1 <上のモジュール名（tests. を除く）>`（木 `C:\dev\kyuura-engine-u7verify` を根にして実行）
- 除外: 全体のテスト（E3）・監査（E4）・対戦の道具
- 想定: 前回の限定の検証で、このうち 20 モジュール・388 件が約 6 分（2026-11-08 12:03〜12:09）。残りの 10 モジュールの件数・時間は不明（記録・保存のモジュールは対戦を含むので長い可能性がある）。上限: モジュールごとに 1800 秒（監視側の期限。テストの失敗と分けて記録）
- 合格: 全モジュールの終了コード 0・失敗 0・エラー 0。skip は件数と理由を記録する
- 失敗: 原因を調べる。テスト・コードを直したら、直した範囲に関係するモジュールだけを再実行し、元の失敗の行は消さずに残す。コードの不具合なら、総合検証を止めて利用者に報告する（直すのは別の作業）
- あわせて読む確認（実行しない）: 双子のテストが「公開の観測が同じ」ことを先に確かめているかを各モジュールで読み、表にする
- 証跡: `E1/summary.jsonl`・モジュールごとの `.log`（標準出力と標準エラー）

### E2. 生成物・台帳の検査（必須・低負荷）

- 主張: 仕様・設計の生成物と台帳が、固定の木のコードと食い違わない
- コマンド（1 つずつ。根から）: `python scripts/build_legal_actions_api_design.py --check`・`build_legal_actions_u7_5_design.py --check`・`build_implementation_identity_design.py --check`・`build_convention_records.py --check`・`build_diagnostic_catalog.py --check`・`build_diagnostics_replay_api_design.py --check`・`build_state_snapshot_design.py --check`・`build_play_policy_family_plan.py --check`・`build_stop_policy_classification.py --check`・`check_implementation_assumptions.py --check`・`check_normalization_revalidation.py --check`・`check_card_sources.py`・`check_research_links.py`（`../kyuura` の固定コミットがあるとき）。`check_implementation_assumptions.py --sites` は報告だけ（数を合わせるために文を変えない）
- 想定: 各数秒〜数十秒（v0.159 の記録では時間を残していない。不明）
- 合格: 終了コード 0（`--sites` は基点との差を分類する）
- 証跡: `E2/<スクリプト名>.txt`・終了コード

### E3. 全体のテスト（必須・中負荷。単独で）

- 主張: 共有エンジンの回帰がない（U7 で分けた `check_*` と T-F1 のあと、既存のすべてのテストが通る）
- コマンド: 順の道具で `tests/test_*.py` の全モジュールを 1 つずつ（1 worker）。[testing](testing.md) の `python -m unittest` と同じ収集を、モジュールごとの別プロセスに分けたもの
- 対象: 303 モジュール（静的な数え上げ。実行のときに数え直して記録する）
- 想定: v0.159 は 283 モジュール・7,955 件・4,778 秒（最長 `test_card_sources` 484 秒）。今回の件数・時間は不明（U7 で 18 モジュール以上増えた）。上限: モジュールごとに 3600 秒
- 合格: 終了コード 0 でないモジュール 0・期限切れ 0・読み込みの失敗 0・失敗 0・エラー 0。skip は件数と理由（既存の `test_cross_version_compatibility` の大きな比較は `KYUURA_COMPAT_BASE` を設定したときだけ）
- 失敗: E1 と同じ。全体の実行は 1 回だけで、失敗したモジュールだけを直したあと再実行し、別の行として記録する（足し合わせない）
- 次へ進む条件: 合格し、前後の木の指紋が同じ
- 証跡: `E3/summary.jsonl`・`.log`・`fingerprint_after.json`

### E4. 保存・復元の監査を U7 のモジュールへ（必須・中負荷）

- 主張: U7 を通した操作の各状態で、保存・復元が restored になる（P1・P6）
- コマンド: `python -m tools.snapshot_audit tests.<モジュール>`（1 つのプロセスに 1 モジュール）
- 対象: `test_legal_actions_u7_3`・`u7_4`・`u7_5ab`・`u7_5c`・`u7_5d`・`u7_5e`・`u7_5g_energy2`・`u7_5g_face_down_power`・`test_client_api`・`test_chaos_gym_borrow_t_f1`（10 モジュール）。監査は `engine._require_integrity` の位置で保存・復元を試すので、U7 の submit から apply_command に届いた状態が対象になる
- 除外: v0.159 の 12 モジュール（U7 の前の対象。今回の主張ではない）
- 想定: v0.159 は 12 モジュール・434 件で 514 秒。今回のモジュールの時間は不明。上限: モジュールごとに 1800 秒
- 合格: restored でない復元 0・表せない値 0・予期しない失敗 0。テストが差し替えた効果の登録表での保存の拒否（effects）は数えるだけ
- 証跡: `E4/<モジュール>.txt`

### E5. 配布と通常のインストール（必須・低負荷）

- 主張: Git の URL からの通常のインストールと wheel・sdist で、同じ版・同じ実装の識別（P6）
- コマンド（[installation](installation.md)）:
  - `git archive e26df79` から作った木で `python -m build`、`python scripts/check_distribution.py --wheel <whl> --sdist <tar.gz>`
  - クリーンな仮想環境（証跡のフォルダの下）に `pip install "kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@e26df79cc6dec913c1d15b5d8203df066334d65d"`（`-e`・`PYTHONPATH` なし）
  - リポジトリの外を作業ディレクトリにして `<venv>\Scripts\python -I smoke_installed_package.py`（スクリプトを写して実行）
  - `behavior_digest` と 3 つの規約集合の照合値を記録し、前回の記録（`legal-actions-u7-5fg.md` 6.2 節: `07a189c9…6c18`）と比べる
- 合格: `problems=0`・スモークの problems が空・識別が同じ
- 証跡: `E5/`（配布物の sha256・pip freeze・スモークの JSON）

### G0. GUI の固定と準備（低負荷）

- 主張: GUI の作業場所が `b1037bc`・変更なしで、接続層の venv のエンジンが `e26df79` の通常のインストール
- コマンド: `git -C C:\dev\kyuura-engine-gui-wt-u75fg status --short`・`rev-parse HEAD`、`server\.venv\Scripts\python -m kyuura_gui_server.engine_source`（`commit_id`・`version`・`module` の場所が今の作業場所の `.venv` の下）
- ポートの確かめ: 8766・5174 で待ち受けているプロセスがない（`Get-NetTCPConnection -State Listen`）。あれば、pid のコマンド行を記録して止める理由を利用者に聞く（他のセッションのものは止めない）
- 証跡: `G0/`

### G1. 直したのに実行していない e2e（必須・最初の GUI の確かめ）

- 主張: b1037bc の送る前の check の変更のあと、既存の操作の列が実エンジンで通る（P3・P4）
- 対象（実際の呼び出し先を調べた結果。4 ファイル・14 件）:

| ファイル | 件数 | b1037bc で変わった呼び出し |
|---|---|---|
| `web/e2e/turn-basics.spec.ts` | 2 | ファイルの中の `checkAndSubmit`（125・167・205 行） |
| `web/e2e/u75e.spec.ts` | 3 | ファイルの中の `checkThenSubmit`（37 行。エネルギーをつける）と `helpers.attachToActive`（30・62 行） |
| `web/e2e/u75.spec.ts` | 6 | `helpers.attachToActive`（61 行） |
| `web/e2e/attacks.spec.ts` | 3 | `helpers.attachToActive`（33・68・92・97・136 行） |

- コマンド（`web` で。1 ファイルずつ、終わるたびにプロセスを確かめる）: `$env:PLAYWRIGHT_JUNIT_OUTPUT_NAME="<証跡>\G1\<名前>.xml"; npx playwright test e2e/<ファイル> --reporter=list,junit`
- 想定: 前回の作業場所の既存 e2e 23 件の時間は記録がない（不明）。カツラの 1 件は約 14 秒（サーバーの起動を含む）
- 上限: 1 件 120 秒（設定の timeout）。ファイルごとに 20 分
- 合格: 全件成功。失敗は screenshot（only-on-failure）と trace を保存し、原因を調べる。GUI を直す必要があれば総合検証を止めて報告する（直すのは GUI の別の作業）。直したあとは失敗した件だけを再実行し、元の失敗の記録を残す
- 証跡: `G1/` の JUnit・標準出力・失敗の画面

### G2. GUI の通常の回帰（必須）

- 主張: GUI の残りの e2e・接続層・単体・型検査・ビルドが作業場所で通る（P3〜P5）
- 対象と順（1 つずつ）:
  1. 型検査 `npx tsc --noEmit -p tsconfig.json`・ビルド `npm run build`
  2. 単体テスト 18 ファイル（1 ファイルずつ `npx vitest run <ファイル> --reporter=default --reporter=junit --outputFile.junit=<証跡>`）
  3. 接続層のテスト 10 ファイル（1 ファイルずつ `server\.venv\Scripts\python -m pytest server/tests/<ファイル> -c server/pytest.ini -p no:cacheprovider --junitxml <証跡>`）
  4. 残りの e2e: `local-flow.spec.ts`（5）・`card-images.spec.ts`（4）・`u75fg.spec.ts`（4。カツラを含めて今回の行として実行する）
- 想定: 前回の作業場所の単体 221 件・接続層 113 件（ファイルに分けたときの件数は不明）
- 合格・失敗: G1 と同じ
- 証跡: `G2/`

### G3. 本番ビルドの preview（必須）

- 主張: 本番ビルドでも、カード画像と U7-5f・g の画面が動く（P4）
- コマンド: G2 のビルドの成果物のまま（作り直さない）、`$env:KYUURA_E2E_PREVIEW="1"; npx playwright test e2e/card-images.spec.ts --reporter=list,junit`、続けて `e2e/u75fg.spec.ts`（README のコマンドを 1 ファイルずつに分けたもの）
- 想定: 8 件（4＋4）。前回の作業場所の preview は 4 件（どのファイルかは 13.8 に書いていない。JUnit は一時フォルダにある。8.3 節）
- 合格・証跡: G1 と同じ（`G3/`）

### G4. クリーンな場所（必須）

- 主張: GUI を新しく取得した場所で、setup から e2e・preview まで通る（P6）。前回は e2e・preview を実行していない
- 場所: `C:\dev\kyuura-engine-verification-u7\clean\gui-b1037bc`（証跡のフォルダの下。新しく作る。残っていれば止める）
- コマンド（前回の手順 `clean_u75fg.ps1` と同じ形。npm と pip のキャッシュは新しいフォルダ、`PYTHONPATH` は空）: `git clone --branch feature/engine-u7-5fg https://github.com/moheronemy/kyuura-engine-gui.git <場所>`・`git -C <場所> checkout --detach b1037bc`・`npm run setup`・`python -m kyuura_gui_server.engine_source`・G2 の 1〜4（全 e2e 27 件。G1 の 4 ファイルを含む）・G3
- 注意: Playwright の既定のポート（8766・5174）は作業場所の実行と同じ。G1〜G3 の実行が終わり、待ち受けがないことを確かめてから始める
- 証跡: `G4/`（setup のログ・engine_source の出力・JUnit）

### G5. renderer の固定の確かめ（必須・低負荷）

- 主張: GUI の依存の renderer が `af88231` で、導入物が同じ（P6）
- コマンド: `web/node_modules/kyuura-card-renderer/package.json` の `version`・lockfile の `resolved` を記録。renderer のリポジトリは読むだけ
- 証跡: `G5/`

## 5. エンジン側と GUI 側の重点

### 5.1 エンジン

- 一致の比べ（P1）は、outcome・状態（形式 35 の書き出し）・乱数の状態・ログ・決定・3 者の観測を比べる。差があれば、状態の値を書き換えたり項目を除いたりして一致にしない
- 双子（P2）: 本人の知識（本人の手札・本人が知るうらのカードなど）と公開の情報（公開の観測）を同じにし、秘密の配分（相手の手札・山札の並び・うらのカードの本当のカード）だけを変える。双子として使う前に、公開の観測が同じことを確かめる。公開の情報の違う 2 つの対戦は「別の対戦」と呼び、情報境界の確かめに数えない
- refused（client_api が送らない）・rejected（エンジンが拒否し状態はもどる）・accepted のあとの決定待ち・停止・終局を、別の行で数える。拒否のあとに相手・観戦者の更新が 0 件
- energy2: 任意の段の省略（2 段）・2 枚・同じカード・1 段目を変えた古い 3 段目・知らない鍵・逆の順・4 つ以上は `u7_5g_energy2` の範囲。X1 では BLAINE_DECK のほかのデッキでカツラに届く対戦があるかを先に静的に調べる
- FU2: 番のプレイヤーの MAIN だけに表示の候補。送れば `CANDIDATE_NOT_EXECUTABLE`。番でない主体・決定の回答者は R-4 で partial。準備の段階の R-4 は今の確かめの外
- 本人のうらの能力: 本人の候補にだけ。相手・観戦者の応答・観測・ログ・更新が双子で同じ。0・1 段だけ入力を返す。2 段以上は R-3 で入力を返さない。送ったあとの受理（決定はあと）・拒否（状態はもどる）・トラッシュ（たねでない）
- residual: `classes` はどの応答でも同じ値。present の public は公開の状態から、actor は本人の候補から。actor の present は相手・観戦者の応答に出ない。MAIN は R-2 で partial
- PT-5e（`BlainesQuiz`・`BlainesHeightQuiz`・`SetAsideGuessKindQuiz`・`GuessOpponentPrizeKind`・`SwapPleaseTrainer`）と UP-5t（名前で解決できない呼び出しの先）は、この検証で解消しない。`unverified_paths` に出ることと、文書の記録が残ることだけを確かめる

### 5.2 U7 の前の基点と比べるとき（X2）

- 比べる木: `a2c51a1`（U7 の前）と `e26df79`。`git diff a2c51a1 e26df79 -- kyuura_engine` で変わったのは `__init__.py`・`client_api.py`（新しい）・`legal_actions.py`（新しい）・`effects.py`・`engine.py`・`resolution/flow.py` の 6 つ
- 意図した変更の整理:

| 変更 | コミット | 期待する差 |
|---|---|---|
| `check_*` への分け（U7-3 `c25781f`・U7-4 `af00e10`・U7-5ab `6e24cb3`・U7-5c `2df1eec`・U7-5d `c981dd0`・U7-5e `c5f3c5d`） | 確かめの前半を関数に分けた（同じ順・同じコード・同じ文） | 差なし |
| T-F1（F-8・F-9）`d1f123b` | 錯乱ジムの「うら」で相手が使うための条件を満たせないとき、聞かずにトラッシュ（`chaos_not_borrowable`）していたのを、相手に `ACCEPT_REQUEST` を出す（「使う」は拒否・`chaos_answered`）。サイキックコントロールで条件を満たせないカードを選べるものに残す（選ぶと拒否）。公開の情報で満たせない条件も同じ扱い | 該当する局で、相手の答え（`ResolveDecision`）が 1 つ増え、決定の id とその後のログの位置がずれる。乱数の消費は変わらない（`chaos-gym-borrow-t-f1.md` 105 行） |
| `effects.py` の `POWER_INPUT_STAGES` など | 宣言の表を加えた（挙動は変えない） | 差なし |

- 差の扱い: 差のある局を 1 局ずつ、最初の差の歩を特定し（v0.146 5.2 節の方法: 新しい木のコマンドを最初の差の前まで送った状態に、基点の木のその位置のコマンドを送る）、上の表のどれに当たるかを記録する。当たらない差は不具合の候補として止める。期待した差をまとめて除外しない。状態の値を書き換えて一致させない
- lockstep の既定の対戦（自然な対戦とストレスの組）に錯乱ジム・サイキックコントロールが届くかは、実行の前に静的に調べて記録する（届かなければ、この比べで T-F1 の差は出ないことを先に書く）

### 5.3 GUI（確認の範囲の区分）

| 区分 | 何で確かめるか | 数え方 |
|---|---|---|
| 実エンジン・new_game から画面の操作 | e2e の turn-basics・attacks・card-images・local-flow の一部、固定例のうち new_game から始めるもの（halt・lucky_stadium・saffron_gym・secret_plan・clefairy_doll・chaos_gym・rocket_charmander・dark_kadabra・blaine・face_down_power） | 実際の操作で確かめたものに数える |
| 実エンジン・再生した合法な固定例 | decision・sudden_death（pikachu_seed9）・disguise・energy_trans・flash（接続層が公開の `new_game`・`apply_command` で再生した盤面） | 再生した盤面からの操作として、new_game からの操作と分けて数える |
| 構築盤面 | エンジンのテストの直接作った盤面（GUI の e2e には使っていない） | GUI の確かめには数えない |
| 模擬の応答 | web の単体テスト（`mockTransport`・fixtures） | 形を運べることだけ。実際の操作で確かめたことに数えない（R-2・R-5 の present、鍵がない組、1 段のうらの能力、拒否・トラッシュの表示など） |

## 6. 必須の回帰と、費用の大きい追加

### 6.1 必須（この順）

E0 → E1 → E2 → E3 → E4 → E5 → G0 → G1 → G2 → G3 → G4 → G5。E3 は単独で実行し、ほかの段と重ねない。G の段はエンジンの段のあとに始める（同じ端末の資源を分けるため）。

### 6.2 費用の大きい追加（利用者の判断のあと、1 つずつ）

| 番号 | 内容 | 必要な理由 | 小さい代わり | 上限の案 |
|---|---|---|---|---|
| X1 | U7 だけで対戦を進め、各歩で直接と比べる新しい道具（3 集合。各歩で candidates・inputs・check の前後の状態を比べ、送ったコマンドを直接にも送って比べる。拒否の候補・不正な入力を混ぜる） | 今の U7 の確かめはすべて固定の少数の盤面で、U7 を通した長い対戦の一致・副作用のなさは確かめていない（3.1 節）。どのツールも legal_actions を使わない | 既存の lockstep の自然な対戦の方策（`tests/test_*_games*.py` の `play_game`）を U7 の候補の選び方に置きかえた小さな対戦（例: 3 集合 × 2 デッキの組 × seed 5 × 600 歩） | 対戦数・歩の上限を先に固定し、結果を見て選び直さない。メモリ 2,500 MB 以上の空きを確かめてから。道具は新しいコードなので、置き場所（リポジトリの `tools/` に入れるか証跡だけか）を先に決める |
| X2 | lockstep `a2c51a1` と `e26df79`（既定の 760 局。今の挙動・S2A・PO） | 共有エンジンの `check_*` の分けと T-F1 の差の範囲を、U7 の前と比べて示す | E3 の全体のテストだけ（意図した差の局を特定できない） | 1 つずつ順に記録。v0.159 の記録は 1 回あたり約 215 秒（今の挙動）。S2A・PO は不明 |
| X3 | `tools/existing_effect_games.py` の 108 バッチ・4,356 局（3 集合） | 過去の計測と同じ構成で、自然な対戦の終わり方・停止の頻度を比べる | T-F1 の差が届くデッキ（錯乱ジム・サイキックコントロールを持つデッキ）のバッチだけを、v0.146 と同じく静的に選んで実行 | 全体は必要としない。U7 の新しい処理（legal_actions）はこの道具を通らないので、U7 の確かめにはならない |
| X4 | `tools/stress_engine.py` の広い実行 | 不正なコマンドを混ぜた長い対戦での不変条件 | E3 に含まれるストレスのテスト・X2 のストレスの組 | 既定（seed 40・600 歩）を超えない。U7 を通らない |

108 バッチ・4,356 局などの過去の規模を、今回の必要量にしません。U7 で変わった共有エンジンは確かめの関数の分けと T-F1 だけで、その範囲は E3・X2 と対象を選んだ X3 で示せます。U7 そのもの（候補・入力・check）は X3・X4 の道具を通らないので、U7 の網羅を示すには X1 が要ります。

## 7. 資源と実行の管理

- 重い処理（E3・E4・X1〜X4・G の e2e）は並列にしない。1 つの段の中も 1 つずつ
- テストは 1 モジュール（GUI は 1 ファイル）ずつ別のプロセス。過去に、多くのモジュールを 1 つのプロセスにまとめた実行がメモリ不足で止まった（`chaos-gym-borrow-t-f1.md` 121 行・`play-set-verification-v0.146.md` 6.2 節・`baby-rules-evolution-v0.114.md` 445 行）
- 各対象の開始・終了・件数・終了コードを JSON Lines に書く（順の道具）。中断した実行は別の行（`status: interrupted`）にし、成功・失敗の数に入れない
- 資源不足で止まったら: 止まった対象・時刻・残ったプロセス（python・node・msedge の pid とコマンド行）を記録し、利用者に報告する。自動で重い再実行をしない
- 失敗したら: 原因を調べ、直したあと必要な対象だけを再実行する。元の失敗の記録を残し、再実行の行と足し合わせない
- 件数を確かめるために、成功した検証を再実行しない（JUnit・summary から読む）
- 同じ実行・重なる実行を合算しない（E1 と E3 は別の行。E3 の数に E1 を足さない）
- 監視側の期限: エンジンのモジュールは 3600 秒（E1・E4 は 1800 秒）、e2e は設定の 120 秒／件

### 7.1 GUI のサーバーのプロセス

- `/api/health` は版と契約だけを返し、pid・場所は返さない（`app.py` 125〜128 行）。版だけでは作業場所を見分けられない
- 始める前: 8766・5174（e2e）・8765・5173（開発）の待ち受けを `Get-NetTCPConnection -State Listen` で調べ、あれば pid とコマンド行（`Get-CimInstance Win32_Process`）を記録する。今回の作業場所のものでなければ止めない
- 実行中: Playwright が起動した接続層・Vite の pid を、待ち受けのポートから引き、コマンド行に今回の作業場所の場所（`...\server\.venv\Scripts\python.exe`・`...\web`）が入っていることを確かめて記録する。あわせて `python -m kyuura_gui_server.engine_source` の `module` が同じ作業場所の `.venv` の下であることを確かめる
- 終わったあと: Playwright が止めることを確かめる（待ち受けがない。`OwningProcess` 0 の TIME_WAIT は数えない）。残っていれば、記録した pid のうちコマンド行が今回の作業場所のものだけを `Stop-Process -Id <pid>` で止める。他のセッションのプロセスは止めない
- 開発サーバー（`npm run dev`）を手で起動したときも同じ手順で記録し、起動した pid だけを止める

## 8. 証跡の保存

### 8.1 保存先

- 恒久の保存先: `C:/dev/kyuura-engine-verification-u7/`（リポジトリの外。停止の方針の台帳の作成スクリプトが読む `C:/dev/kyuura-engine-verification/` の下ではない。v0.137・v0.138・v0.159 と同じく別のフォルダ）
- セッションの一時フォルダだけに置かない。実行の作業場所から、段が終わるたびに写し、写す前後で sha256 を比べる
- 文書からの参照: 総合検証の結果の文書（実行のあとに作る）に、保存先・`MANIFEST.md`・`sha256.json` の sha256 を書く。Git には入れない

### 8.2 中身

```
kyuura-engine-verification-u7/
  MANIFEST.md          # 段ごとの対応（対象・コマンド・結果・未実行・再実行）
  manifest.json        # 同じ内容の機械向け
  sha256.json          # 全ファイルの sha256
  public/              # 閲覧者に見せてよいもの（集計・JUnit・ログの要約・画面）
    E0/ … E5/ G0/ … G5/
  verifier/            # 検証者用（秘密を含む。閲覧者に渡さない）
    full-records/      # 完全な記録・スナップショット・lockstep の記録・seed とデッキの対応
  clean/               # G4 のクリーンな場所（実行のあとの状態のまま）
  preserved/           # 既存の一時の証跡を写したもの（8.3 節。作り直さない）
```

- 保存するもの: 対象のコミット・依存の固定（requirements.txt・package-lock.json の該当行）・導入元（`engine_source`・`direct_url.json`）・環境とツールの版、実行のコマンド・開始・終了・終了コード・件数、JUnit・標準出力・標準エラー、比べの条件・期待した差・実際の差（5.2 節の表の形）、ブラウザの失敗の記録（screenshot・trace）と必要な画面、中断・未実行・再実行の記録、証跡の一覧と sha256
- 分けるもの: 完全な記録（seed・山札の並び・うらのカードの本当のカード・相手の手札）・スナップショット・lockstep の記録は `verifier/`。閲覧用記録（U5 の本人・観戦者の記録）と集計は `public/`。GUI の e2e の画面は本人の画面だけ（相手の手札などの秘密は出ない）なので `public/`。trace は通信の中身を含むので `verifier/`

### 8.3 既存の一時の証跡（所在と読めることを確かめただけ。移動・削除はしていない）

| 証跡 | 場所 | 確かめたこと |
|---|---|---|
| U1〜U6 の総合検証 | `C:/dev/kyuura-engine-verification-v0.159/`（2,621 ファイル・`MANIFEST.md`・`sha256.json`） | 恒久。`full/summary.json` が読める（283 モジュール・7,955 件・失敗 0） |
| U7-5f・g の限定の検証（エンジン） | セッションの一時フォルダ `…\Temp\claude\29f7fafcfd7def4f\eae48010-…\scratchpad\fg\final\summary.jsonl` など（`fg`・`u75`・`pkg`） | 読める（20 モジュール・388 件・12:03〜12:09） |
| GUI の U7-5f・g の前回の検証 | `…\Temp\claude\1101945aea60821a\9a5faf67-…\scratchpad\`（`junit_e2e_u75fg_new.xml`・`_existing.xml`・`_rerun3.xml`・`_preview.xml`・`junit_clean_u75fg_server.xml`・`_web.xml`・`clean_u75fg.log`） | 読める。数は GUI の 13.8 と合う（新しい e2e 4・既存 23 のうち failures 1・errors 2・再実行 3 成功・preview 4・クリーンな場所の接続層 113・単体 221） |
| GUI の今回（b1037bc の前の作業場所）の検証 | `…\scratchpad\gui\runs\`（このセッション） | 読める（型検査・単体 184・接続層 13・ビルド・e2e 1） |

- 一時フォルダは消えることがあります。総合検証の E0 で `preserved/` に写して sha256 を記録することを提案します（写すだけ。中身を書き換えない）。残っていない証跡を作り直して、当時の実行の結果として扱いません

## 9. 残る判断事項と、この計画で保証しないこと

判断が要るもの:

1. X1（U7 だけで対戦を進める新しい道具）を作るか、作るなら置き場所（リポジトリの `tools/` に入れて固定するか、証跡だけか）と上限
2. X2〜X4 を実行するか。X3 は T-F1 の届くバッチだけにするか
3. E1・G1 で見つかった不具合を直す作業を、総合検証の中で行うか、止めて別の作業にするか（この計画は止めて報告する）
4. 一時の証跡を `preserved/` に写すか
5. 1.4 節の文書の食い違いの訂正（GUI の 13.8・README は GUI の作業。エンジンの `legal-actions-api-implementation-plan.md` は結果の文書で直す）

保証しないこと:

- 全効果の完走・受理（`unverified_paths`・PT-5e・UP-5t・受理のあとの停止）
- R-2〜R-5 の解消（未対応のまま。表示と範囲の正しさだけを確かめる）
- 模擬の応答だけの経路の実際の操作（5.3 節）
- Windows 以外の環境・Edge 以外のブラウザ
- 過去の参照データの作り直し（T-F1 の差は旧版との違いとして残る）
- エンジンの main・GUI の main・renderer の main の先頭（対象は 1.1 節のコミットだけ）

## 10. この文書の作成で実行したこと・していないこと

- 実行した: 3 つのリポジトリの履歴・リモート・未コミットの変更の読み取り（`git fetch`・`rev-parse`・`branch --contains`・`status`）、文書とコードの読み取り、静的な数え上げ（テストのモジュールのファイルの数・e2e の呼び出し先）、既存の一時の証跡の JUnit・summary を読むこと
- 実行していない: テスト・ビルド・対戦の探索・lockstep・監査・配布の確かめ・GUI のサーバーの起動・総合検証。依存の更新もしていない
