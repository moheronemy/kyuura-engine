# 診断 API と対戦記録・再現インターフェースの仕様案

この文書は**仕様案**です（状態 `proposed`、承認 `not_approved`）。v0.152 で、利用者が U1（診断の型と情報境界）・U2（コマンド実行結果のアダプタ）と 6 つの方針だけを採用し、実装しました（[diagnostics-adapter-v0.152.md](diagnostics-adapter-v0.152.md)。採用の記録は下の「採用の記録」）。v0.153 で、利用者が U3（完全な再現用記録の収集・形式・構造の検証）と 4 つの方針（実装の識別・実行環境・確認値の密度・形式の版）を採用し、実装しました（[replay-record-v0.153.md](replay-record-v0.153.md)）。v0.154 で、利用者が U4（記録からの再実行と確認値の照合）の実装と限定検証を承認し、実装しました（[replay-run-v0.154.md](replay-run-v0.154.md)）。v0.155 で、利用者が U5（閲覧用記録）と方針を採用し、実装しました（[view-record-v0.155.md](view-record-v0.155.md)）。状態の保存と復元（U6）は、v0.156 で原則だけを採用し、仕様案と実装計画（案）を作りました（[state-snapshot-design.md](state-snapshot-design.md)・[state-snapshot-implementation-plan.md](state-snapshot-implementation-plan.md)）。v0.157 で、利用者が判断事項 6 件を採用し、S1〜S4・S6（書き出し・読み取り・復元・継続の一致・最小のホストへの接続）を実装しました（[state-snapshot-v0.157.md](state-snapshot-v0.157.md)。S5 は未実装なので、U6 全体は planned のまま）。合法手の一覧（U7）・異なる版と規約集合の比べは、仕様案のままで実装していません。9 章の例は形の例示です（`api_status` は `illustrative`。実際の出力の例は v0.152 の文書）。実装の単位と順は [実装計画](diagnostics-replay-api-implementation-plan.md) に、利用者の判断が要る事項もそこに書きます。

構造化した仕様は [diagnostics-replay-api-design.json](diagnostics-replay-api-design.json) です。この文書の表と例（`<!-- generated:… -->` の区画）は、JSON と同じ元（`scripts/build_diagnostics_replay_api_design.py` の `SPEC`）から作ります。区画の中を手で直さないでください（`--check` が違いを見つけます）。区画の外の説明は手で書いています。

## 採用の記録

<!-- generated:adoptions begin -->
- `ADOPT-U1-U2`（2026-11-06・利用者）: U1（診断の型と情報境界）と U2（コマンド実行結果のアダプタ）の実装と、次の方針だけ。仕様案のほかの判断事項・仕様案の全体の承認ではない。実装: v0.152（docs/diagnostics-adapter-v0.152.md）
  - 方針:
    - 本人向けの説明は、原則としてコードに対応する安全な定型文とする
    - 生の例外文と内部の詳細は検証者用とし、通常の閲覧者へ渡さない
    - 状態の不整合は、本人にも一般的な説明だけを返す
    - 未登録コードを推測で未裁定・未対応へ分類しない。診断の対応漏れとして検出する
    - 拒否された操作は、将来の完全記録へ任意で残せる設計にする。受理した操作の再現とは区別する
    - 対戦後も情報の公開範囲を自動では広げない
  - 判断事項: D-MESSAGE、D-STATE-INTEGRITY-VIEW、D-REJECTED、D-POSTGAME
  - 実装単位: U1、U2
- `ADOPT-U3`（2026-11-06・利用者）: U3（完全な再現用記録の収集・形式・構造の検証）の実装と、次の 4 つの方針だけ。スナップショットの形式・停止状態の保存・U4 以後の承認ではない。実装: v0.153（docs/replay-record-v0.153.md）
  - 方針:
    - 実装の識別: エンジンの版に加え、挙動に関係するソースと同梱データの内容のハッシュを記録する。Git のコミットは補助の情報で、Git がなくても識別できる
    - 実行環境: 再現の保証を、対応する Python の実装・版に限る。異なる環境で同じ結果になるとは保証しない。OS・パス・改行など意味に影響しない違いまで無条件に非対応にしない
    - 確認値の密度: 受理した操作ごとに、状態と乱数の確認値を残す（U4 で最初の不一致を特定できるように）
    - 形式の版: 再現用記録の形式の版を独立して設ける。診断の形式・状態の形式・規約集合の版はそれぞれ参照する。新しい版の管理の方法を、保留中のほかの形式へ一括で当てはめない
  - 判断事項: D-IMPLEMENTATION-ID、D-RUNTIME、D-CHECK-DENSITY、D-VERSIONS
  - 実装単位: U3
- `ADOPT-U4`（2026-11-06・利用者）: U4（完全な再現用記録からの再実行と確認値の照合）の実装と限定検証だけ。閲覧用記録・スナップショットの復元・異なる版と規約集合の比べ（compare_runs）・未決の判断事項の承認ではない。実装: v0.154（docs/replay-run-v0.154.md）
  - 方針:
    - 初期状態を含む確認値を照らす
    - 拒否を含む記録は seq の順に処理する（受理だけを先に送らない）
    - 失敗・不完全な記録と、正常な再現の成功を区別する
    - PYTHONHASHSEED による影響を確かめる
    - 操作を受理した結果として停止する経路を確かめる
    - 確認値から pending_moves などを除いている根拠を確かめ直す
  - 判断事項: 
  - 実装単位: U4
- `ADOPT-U5`（2026-11-06・利用者）: U5（閲覧用記録）の実装と次の方針だけ。スナップショットの形式・停止状態からの再開・対戦後の完全な情報の公開の承認ではない。実装: v0.155（docs/view-record-v0.155.md）
  - 方針:
    - 閲覧用記録に、完全な再現用記録とは別の形式の版を設ける（kyuura_view_format）
    - 各時点の observe・閲覧用ログ・view_for を元に作る
    - 最後の状態の知識を過去の場面へ遡って入れない
    - 拒否した操作は本人の記録だけに入れ、相手・観戦者には存在も知らせない
    - 完全な記録の seq を、閲覧用記録に出さない
    - seed・乱数の状態・完全な状態の確認値・非公開の初期の条件・完全なコマンドを写さない
    - 閲覧用記録からの再実行・状態の復元は保証しない
    - 対戦が終わったあとも閲覧の範囲を自動では広げない
  - 判断事項: 
  - 実装単位: U5
- `ADOPT-U6-PRINCIPLES`（2026-11-06・利用者）: U6（JSON の状態の保存・復元）の仕様の作成と原則だけ（docs/state-snapshot-design.md 3 章）。スキーマの細部・自動移行の方法・U6 の実装の承認ではない。実装: 仕様だけ（docs/state-snapshot-design.md・docs/state-snapshot-implementation-plan.md）。U6 は未実装
  - 方針:
    - 形式 35 をそのまま復元の形式に使わず、必要な全状態を明示した独立の形式にする
    - 初めの対応範囲は、同じ実装・依存データ・規約集合に限る
    - カード定義・規約は、原則として識別から登録済みのものを解決する
    - 乱数の状態を正確に保存・復元する
    - 決定待ちを保存・復元の対象に含める
    - HALTED・途中停止も保存・復元できる設計にする。停止の解除・未対応の続行は認めない
    - 不正・未知の状態を推測で補ったり移したりしない
    - スナップショットは完全な情報を持つホスト用で、閲覧用記録と分ける
    - 完了の基準は、復元のあとの同じ操作の列で状態・乱数・ログ・観測が同じこと
  - 判断事項: D-SNAPSHOT-BASE、D-HALT-SNAPSHOT
  - 実装単位: 
- `ADOPT-U6-IMPL`（2026-11-07・利用者）: U6 の S1〜S4・S6（状態スナップショットの書き出し・読み取り・復元・継続の一致・最小のホストへの接続）の実装と、スナップショットの仕様の判断事項 6 件（DS-CONSTRUCTED・DS-HALT-TEXT・DS-CHECK・DS-DEPTH・DS-RECORD-LINK・DS-INSTRUMENTATION。docs/state-snapshot-design.json）。S5（完全な記録の途中から再開して U4 で照らす）は別の作業。実装: v0.157（kyuura_engine/snapshot.py。docs/state-snapshot-v0.157.md）。S5 が未実装なので、この表の U6 は planned のまま
  - 方針:
    - 構築盤面も、保存の境界と整合の確かめを満たせば保存できる（new_game から合法に到達できることは保証しない）
    - 停止の理由の文も保存する。閲覧者への表示は診断 API の安全な文
    - 保存したときの確認値を入れる（照らすためのもので、署名・認証・改ざんの防止ではない）
    - 入れ子の深さの上限を固定し、同じ上限を保存と読み取りに当てる
    - 完全な再現用記録への対応は任意の補助情報
    - 初版は記録・診断の部品の識別も一致を求め、違えば非対応
  - 判断事項: 
  - 実装単位: 
<!-- generated:adoptions end -->

採用は、この記録の範囲だけです。v0.152 の時点では実装の識別・Python の環境・確認値の密度・版の分け方も保留でしたが、v0.153 の採用（`ADOPT-U3`）で決めました。スナップショットの形式（D-SNAPSHOT-BASE）と停止状態のスナップショット（D-HALT-SNAPSHOT）は保留（`pending`）のままです。v0.156 の原則の採用（`ADOPT-U6-PRINCIPLES`）で、この 2 つは決まりました（形式 35 を使わない独立の形式・停止も保存できるが解除しない）。具体的なスキーマは[state-snapshot-design.md](state-snapshot-design.md) で、v0.157 の採用（`ADOPT-U6-IMPL`）で判断事項を決めて実装しました。

## 1. 目的と範囲

v0.135〜v0.151 の情報漏れの修正では、「受理・拒否・拒否の理由の文が、見えないカードの配分で変わらない」ことを、テストの道具（双子の比較）で確かめてきました。この約束は、今は `apply_command` の呼び出し元（テスト）の中にしかありません。今後の JSON の保存・復元、合法手の API、GUI のアダプタ、ルールベースの AI、オンライン対戦は、どれも同じ問いを持ちます。

- 操作がどうなったか（受け付けた・拒否した・処理できなかった）を、機械が判定できる形で受け取る
- その結果を、だれにどこまで見せてよいか
- 対戦を記録し、あとで同じ結果を作り直せるか

この仕様案は、その共通の契約を決めます。対象は次の 7 つです: 診断の分類と項目（4 章）、見る人ごとの情報境界（5 章）、記録の 3 つの種類（6 章）、再現のインターフェース（7 章）、版と互換性（8 章）、具体例（9 章）、実装計画（別の文書）。

しないこと: エンジンの動作の変更、API・保存と復元の実装、続行規約の採用、オンライン対戦・画面の実装。

## 2. 基点と調べたもの

- 基点: `7e4a875`（v0.151 の最後。`origin/claude/deck-search-stop-oracles`。`origin/main` の `8d4beff` はその祖先）。エンジンの版は 0.151.0 のまま
- 調べたもの（現行のコード）: 公開 API（`kyuura_engine/__init__.py`）、コマンドの入口（`engine.apply_command`・`apply_command_traced`）、例外（`errors.py`・`conventions.ConventionSetError`）、停止（`state.Phase`・`Halt`・`Interruption`）、決定（`PendingDecision`・`observation._decision`）、観測とログの写し（`observation.py`）、状態の書き出し（`serialize.py` の形式 1〜35 と互換性の約束）、乱数（`rng.py`）、規約集合（`conventions.py`）、知らない再開先・旧状態の拒否（`engine.supported_decision_error`・`decisions.RETIRED_DECISIONS`・`conventions.require_state_conventions`）、サドン・デス（`StartSuddenDeath`・`SegmentRecord`・`tools/sudden_death_games.py`）、1 歩ごとの記録（`tools/engine_lockstep.py` の記録の形式 2）、ログの監査と双子の比較（`tests/log_audit.py`）、停止の方針の台帳（`docs/stop-policy-classification.json`）と同梱の場面の索引
- 読んだ文書: [api-review](api-review.md) 1 章（記録は「デッキ 2 つ・seed・コマンドの列」で十分という v0.2a の見方）、[ruleset-foundation-v0.142](ruleset-foundation-v0.142.md)（版の分離）、[play-set-verification-v0.146](play-set-verification-v0.146.md) 2 章（lockstep の記録の形式 2）、[sudden-death-v0.134](sudden-death-v0.134.md)、v0.147〜v0.151 の文書の引き継ぎ事項（[v0.150](deck-search-decision-presence-v0.150.md) 7 章・[v0.151](deck-search-stop-oracles-v0.151.md) 8 章）

## 3. 現況（既存の機能と再利用の範囲）

状態の語彙: `implemented`（公開・パッケージの中で動く）、`internal_only`（パッケージの中にあるが公開の約束がない）、`tool_only`（テスト・道具だけ）、`not_implemented`（ない）。

<!-- generated:existing begin -->
| ID | もの | 状態 | 参照 | 今あるもの | 再利用 | 限界 |
|---|---|---|---|---|---|---|
| EX-APPLY-COMMAND | コマンドの入口 apply_command | implemented | `kyuura_engine/engine.py::apply_command`<br>`kyuura_engine/errors.py::EngineError` | 状態を複製して処理し、新しい状態を返す。EngineError（拒否）では渡した状態・乱数・ログを変えない（errors.py の約束） | コマンド実行結果のアダプタ（U2）は、これを包むだけにする。受理・拒否の判定をアダプタで作り直さない | 結果は例外か状態。分類・処理段階・見る人ごとの写しはない。EngineError でない例外（RuntimeError など）は、そのまま上に出る |
| EX-ERRORS | 例外の種類とコード | implemented | `kyuura_engine/errors.py::IllegalActionError`<br>`kyuura_engine/errors.py::UnsupportedError`<br>`kyuura_engine/errors.py::StateIntegrityError`<br>`kyuura_engine/errors.py::DeckValidationError`<br>`kyuura_engine/conventions.py::ConventionSetError`<br>`kyuura_engine/errors.py::HiddenPropertyRead` | code（短い名前）と message（説明の文）。UnsupportedError は未裁定（UNRESOLVED_）・未対応（UNSUPPORTED_）・技術的制限・互換性の拒否をまとめて表す | 診断の code はこの code をそのまま使う。分類は例外の種類だけで決めず、台帳の分類と合わせて決める（classification_rules） | UnsupportedError の中の区別（未裁定・未対応・上限・互換性）は例外の種類からは分からない。事例（case）を例外が持たない |
| EX-HALT | 停止（HALTED）と途中停止の記録 | implemented | `kyuura_engine/state.py::Phase`<br>`kyuura_engine/state.py::Halt`<br>`kyuura_engine/state.py::Interruption`<br>`kyuura_engine/interruption.py::public_record` | どの操作でも避けられない停止は、拒否ではなく HALTED の状態を返す（halt.code・message・references・interruption）。ログ halted はコードだけを全員に見せる | 操作の結果が停止になった場合（status=halted）の診断は、halt.code・interruption の公開の記録から作る | HALTED は終端で、再開する API はない（GAP-DEFERRED-HALT-NO-RESUME）。halt.message は診断用の文で観測に入らない |
| EX-DECISION | 保留中の決定と観測の決定 | implemented | `kyuura_engine/state.py::PendingDecision`<br>`kyuura_engine/observation.py::_decision`<br>`kyuura_engine/commands.py::ResolveDecision` | 決定の id・種類・決めるプレイヤー・選ぶ数は全員に、選べるものは決めるプレイヤーにだけ見せる | status=awaiting_decision の診断と、閲覧用記録の決定は、観測の決定の形をそのまま使う | resume・context は内部の続きの情報（観測に入らない） |
| EX-OBSERVE | 観測とログの写し | implemented | `kyuura_engine/observation.py::observe`<br>`kyuura_engine/observation.py::visible_log`<br>`kyuura_engine/observation.py::visible_segment_logs`<br>`kyuura_engine/observation.py::visible_event` | 見る人（0・1・観戦者 None）ごとの盤面とログ。知らないイベントの種類は ValueError（黙って全部を見せない） | 閲覧用記録（B）は、観測とログの写しから作る。新しい見える範囲の表を作らない | 持ち主が知っているデッキリスト・所有者の変更は観測に入らない（v0.137 の owned_card_ids は検査の道具）。拒否された操作は状態を変えないので、ログにもない |
| EX-STATE-EXPORT | 状態の書き出し（形式 1〜35） | implemented | `kyuura_engine/serialize.py::state_to_dict`<br>`kyuura_engine/serialize.py::FORMAT_VERSIONS` | 内部の完全な記録の書き出し（一方向）。形式 35 はエンジンの版と規約集合の識別を持つ。seed と乱数の状態の指紋（rng_state_sha256）を含む | 再現用記録（A）の歩ごとの確認値（状態の指紋）に使う（engine_lockstep と同じ） | 書き出しから状態をもどす関数はない。乱数の状態そのものは入らない。形式 35 が状態を落とさず表すことは確かめていない。プレイヤーに渡してはいけない |
| EX-RNG-JSON | 乱数の状態の保存・復元 | implemented | `kyuura_engine/rng.py::rng_state_to_json`<br>`kyuura_engine/rng.py::rng_from_json`<br>`kyuura_engine/rng.py::rng_fingerprint`<br>`kyuura_engine/rng.py::RNG_FORMAT` | メルセンヌ・ツイスタの状態の JSON と、知らない形式の拒否 | 状態スナップショット（C）の乱数の部分に使う | 状態全体の復元には使われていない |
| EX-PICKLE | Python の状態の写し（pickle・clone） | internal_only | `kyuura_engine/state.py::GameState`<br>`kyuura_engine/state.py::__setstate__` | 前の版の写しを後の版で読む向きの互換（項目の既定値） | 再利用しない（保存の形式にしない） | 安全な外部のデータ交換の形式ではない。後の版の写しを前の版で読む向きは約束しない |
| EX-CONVENTION-ID | 規約集合の識別と確かめ | implemented | `kyuura_engine/conventions.py::ConventionSetIdentity`<br>`kyuura_engine/conventions.py::resolve_for_new_game`<br>`kyuura_engine/conventions.py::require_state_conventions`<br>`kyuura_engine/conventions.py::legacy_problems` | 集合 ID・版・照合値・区分・完全性・構成の規約。状態の集合を扱えなければ UNSUPPORTED_CONVENTION_SET | すべての記録の見出しと、再現の前の確かめに、record() の形をそのまま使う | 照合値は内容の識別で、署名・認証ではない |
| EX-COMMAND-CODEC | コマンドの辞書への変換 | implemented | `kyuura_engine/commands.py::command_to_dict`<br>`kyuura_engine/commands.py::command_from_dict` | 知らない種類は UNKNOWN_COMMAND、足りない・余分な項目は BAD_COMMAND | 再現用記録の操作の列の形にする | コマンドの選んだ値（山札のカードの uid など）は秘密の情報を含みうる（閲覧用記録には入れない） |
| EX-RESUME-GUARD | 知らない再開先・前の版の決定の拒否 | implemented | `kyuura_engine/engine.py::supported_decision_error`<br>`kyuura_engine/decisions.py::unsupported_decision_error`<br>`kyuura_engine/decisions.py::RETIRED_DECISIONS` | 観測・コマンドの前に UNSUPPORTED_DECISION。続けるのに要る情報が欠ける状態は StateIntegrityError | スナップショットの復元（U6）の確かめに、同じ入口を使う | 前の版（v0.139 以前）の動きは変えられない |
| EX-SUDDEN-DEATH | サドン・デスの区間 | implemented | `kyuura_engine/commands.py::StartSuddenDeath`<br>`kyuura_engine/state.py::SegmentRecord`<br>`kyuura_engine/engine.py::_start_sudden_death`<br>`kyuura_engine/sudden_death.py::archive` | 延長戦を始めると、前の区間のログ・結果・所有者の変更を segments に移す。乱数は前の区間から続ける（seed にもどさない） | 記録の区間の境界は StartSuddenDeath の歩と segments の番号で表す | 区間の記録の検査（segment_problems）と延長戦を通す対戦は検証用の道具（tools/sudden_death_games.py） |
| EX-LOCKSTEP | 1 歩ごとの記録と比べ（engine_lockstep） | tool_only | `tools/engine_lockstep.py::Recorder`<br>`tools/engine_lockstep.py::RECORD_FORMAT`<br>`tools/engine_lockstep.py::DIGEST_EXCLUDED` | 見出し（record_format 2・digest_format・規約集合）と歩ごとの記録（コマンドの指紋・受理か拒否の種類とコードと理由の文の指紋・状態の指紋 h・規約集合の指紋 k）。集合の違う記録の比べは --cross-set で別扱い（終了コード 3） | 再現用記録（A）の歩の記録の項目と、版・規約集合をまたぐ比べ（U4 の compare_runs）は、この形と契約を元にする | コマンドは指紋だけ（コマンドそのものがないので記録から再実行できない）。対戦は方策（play_game・choose_command）を再実行して作る。ふだんのテストでは走らない |
| EX-LOG-AUDIT | ログの監査 | tool_only | `tests/log_audit.py::log_problems` | new_game から進めたログだけから場を組み立て直し、状態と同じかを確かめる | 再現の検証（verify_record）の追加の確かめとして呼べる候補 | テストの道具（パッケージに入っていない） |
| EX-TWIN-AUDIT | 双子の比較（拒否による情報漏れ） | tool_only | `tests/log_audit.py::twin_command_problems`<br>`tests/log_audit.py::command_outcome`<br>`tests/log_audit.py::public_view`<br>`tests/log_audit.py::owned_card_ids` | 公開の情報が同じで見えない配分だけが違う状態に同じ操作を送り、受理・拒否・コード・理由の文が変わらないかを比べる | 診断の写し（見る人ごと）が配分によらないことの回帰テスト（U1・U2）に使う | テストの道具。双子を作る swap_hidden・swap_set_aside は各版のテストにある |
| EX-STOP-LEDGER | 停止の方針の台帳と場面の索引 | implemented | `docs/stop-policy-classification.json`<br>`kyuura_engine/data/convention_records.json`<br>`kyuura_engine/conventions.py::scenes_for_code`<br>`kyuura_engine/conventions.py::continuation_lookup` | 停止コードごとの分類（A エンジン機能不足・B 技術的制限・C 未裁定・E 内部ガードなど）・止め方・事例（コード#事例）。同梱の索引はコードから場面を引く | 診断の分類と事例 ID の元にする（新しいコード表を手で作らない） | 台帳は文書で、エンジンは実行中に読まない（同梱の場面の索引だけを読む）。事例を特定できるのは事例が 1 つのコードか、照会で事例を渡す場所だけ |
| EX-TRACE | 解決の記録（内部の入口） | internal_only | `kyuura_engine/engine.py::apply_command_traced` | ワザ・番の終わりの解決の記録（先読みの枝を含む）。状態に保存しない | 開発用の詳細（developer_detail）の候補。検証者だけ | 公開の API ではない。秘密の配分を含む |
| NI-STATE-RESTORE | 状態の保存・復元（v0.157 で U6 の S1〜S4・S6 として実装。形式 kyuura_snapshot_format） | implemented | `kyuura_engine/snapshot.py::save_snapshot`<br>`kyuura_engine/snapshot.py::restore_snapshot`<br>`kyuura_engine/snapshot.py::RestoredGame`<br>`docs/state-snapshot-design.md`<br>`docs/state-snapshot-implementation-plan.md` | ホスト用のスナップショットの書き出し・安全な読み取り・7 段の復元と結果の分類・復元した状態から HostedGame で続ける入口（v0.157） | S5（完全な記録の途中から再開して U4 で照らす）が使う | 形式 35 を読み込み用に読み替えない。同じ実装・依存データ・規約集合だけ。完全な記録との接続（S5）はない |
| NI-LEGAL-MOVES | 合法手の一覧 | not_implemented | `tools/stress_engine.py::choose_command` | ない（ストレス実行の操作の選び方は検証用の道具で、合法手の一覧ではない） | U7 で境界だけを決める | でたらめな操作を混ぜる道具 |
| NI-DIAGNOSTIC | 構造化した診断（v0.152 で U1・U2 として実装） | implemented | `kyuura_engine/diagnostics.py::classify_error`<br>`kyuura_engine/adapter.py::submit`<br>`kyuura_engine/data/diagnostic_catalog.json`<br>`scripts/build_diagnostic_catalog.py` | コード表による分類・見る人ごとの結果（本人・相手と観戦者）・検証者用の記録・コマンド実行結果のアダプタ（v0.152） | U3 以後の記録・再現は submit の結果（CommandResult）を受け取る | 記録・再現・合法手の一覧はない |
| NI-REPLAY-RECORD | 完全な再現用記録（v0.153 で U3 として収集・読み書き・構造の検証を実装。再現は未実装） | implemented | `kyuura_engine/replay_record.py::ReplayCollector`<br>`kyuura_engine/replay_record.py::validate_record`<br>`tests/helpers.py::replay` | 記録の収集（ReplayCollector）・JSON の読み書き・構造の検証（v0.153）。テストの replay はコマンドの列を順に送るだけ | U4（v0.154。kyuura_engine/replay_run.py の replay）が記録の行を seq の順に再実行し、確認値と照らす | 異なる版・規約集合の比べ（compare_runs）はない |
| NI-VIEW-RECORD | 閲覧用記録（v0.155 で U5 として実装） | implemented | `kyuura_engine/view_record.py::ViewHost`<br>`kyuura_engine/view_record.py::ViewRecorder`<br>`kyuura_engine/view_record.py::view_records_from_replay`<br>`kyuura_engine/view_record.py::validate_view_record` | 閲覧者を固定した収集（実行時の収集と、U4 の検証つきの再実行からの変換）・JSON の読み書き・構造の検証（v0.155） | GUI・通信は、閲覧用記録の項目（観測・ログの写し・状態の知らせ）をそのまま使える | 閲覧用記録からの再実行・状態の復元はない |
| NI-HALT-RESUME | 停止からの再開 | not_implemented |  | ない（GAP-DEFERRED-HALT-NO-RESUME） | この仕様の範囲の外（続行規約の採用は別の判断） |  |
<!-- generated:existing end -->

まとめ:

- **再利用できるもの**: 拒否で状態を変えない入口、例外の `code`、停止と途中停止の公開の記録、観測とログの写し（見える範囲の表）、規約集合の識別と確かめ、知らない再開先の拒否、コマンドの辞書への変換、乱数の状態の JSON、台帳の分類と事例。新しい仕組みは、これらを**包む**形にします。分類・見える範囲・コードの表を新しく手で作りません
- **足りないもの**: 構造化した診断、見る人ごとの診断の写し、記録の形式（完全・閲覧用）、記録からの再現、状態の読み込み、合法手の一覧
- **道具にだけあるもの**: lockstep の記録（コマンドが指紋だけで、記録から再実行できない）、双子の比較、ログの監査。これらは設計の元と回帰テストに使い、そのまま公開 API にはしません

## 4. 診断 API の契約案

### 4.1 3 つの区別

利用者の依頼の 3 つは、診断の `outcome` と `status` の組で区別します。

| 場面 | outcome | status | 状態 |
|---|---|---|---|
| 操作を拒否して元の状態を保った | `rejected` | 元の状態の status | 状態・乱数・ログは変わらない（`errors.py` の約束） |
| 操作の結果として停止状態になった | `accepted` | `halted` | 新しい状態（そこまでのコイン・処理が残る終端。途中停止なら `interruption`） |
| 決定の回答を待っている | `accepted` | `awaiting_decision` | 新しい状態（決定の id・種類・決めるプレイヤー） |

停止は拒否ではありません。「どの操作でも避けられない停止」（ポケモンチェック・準備・どの答えでも同じ止め方になる決定）は、今のエンジンでも HALTED の状態を返します（台帳の止め方 `pokemon_check_halt`・`setup_halt`・`deferred_interruption`・`dynamic_halt_conversion`）。診断は、停止の理由を `halt` の項目（分類・コード・事例）に書き、操作そのものの `category` は空にします（例 EX9）。

### 4.2 分類

<!-- generated:categories begin -->
| 分類 | 意味 | 発生元 | 区分 | 状態への影響 | 続けられる |
|---|---|---|---|---|---|
| `invalid_input` | 不正な操作・不正な回答・不正な開始の条件 | IllegalActionError（すべてのコード）、DeckValidationError（INVALID_DECK）、ConventionSetError（INVALID_CONVENTION_SET）、アダプタが new_game の前に確かめる seed の型・範囲 | command, answer, setup | 渡した状態・乱数・ログは変わらない | はい |
| `unresolved_ruling` | 未裁定による停止 | 台帳の分類 C のコード（UNRESOLVED_ の研究上の停止・コードのない問い）と UNRESOLVED_RULING。UnsupportedError の拒否か、HALTED の halt.code |  | 拒否なら状態は変わらない。HALTED なら、そこまでの処理を残した終端の状態 | はい |
| `unsupported` | 未対応・未実装 | 台帳の分類 A のコード（UNSUPPORTED_ のうち互換性・技術的制限でないもの）、UNSUPPORTED_CARD（デッキの検査） |  | 拒否なら状態は変わらない。HALTED なら終端 | はい |
| `technical_limit` | 技術的制限・探索上限 | 台帳の分類 B のコード（UNSUPPORTED_PREFLIGHT_LIMIT・UNSUPPORTED_SECRET_PLAN_IDENTITIES など）と、上限の項目（LIMIT:*） |  | 状態は変わらない | はい |
| `state_integrity` | 状態の不整合 | StateIntegrityError（STATE_INTEGRITY）。処理の前の入力の確かめ（壊れた状態・情報の足りない状態）と処理の後の不変条件 | input, result | 渡した状態は変わらないが、その状態で続けることは保証しない | いいえ |
| `compatibility` | 未知・非対応の規約集合や互換性 | UNSUPPORTED_CONVENTION_SET・UNSUPPORTED_DECISION・UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN（前の版の記録）と、記録・スナップショットの知らない形式・項目・版 | conventions, decision, legacy_state, record_format | 状態は変わらない | いいえ |
| `internal_error` | 内部エラー | EngineError でない例外（RuntimeError・ValueError・KeyError・TypeError など。不変条件の RuntimeError を含む） |  | 保証しない（apply_command は複製で処理するが、内部エラーについては約束していない） | いいえ |
| `unmapped` | 診断の対応漏れ（v0.152 の採用） | コード表にないコード・表と違う例外の型で来たコード（EngineError）、表にない停止のコード |  | EngineError なので渡した状態は変わらない（拒否）。停止のコードなら受理した結果の停止 | はい |
<!-- generated:categories end -->

### 4.3 分類の決め方

<!-- generated:classification-rules begin -->
| 順 | 条件 | 分類 | 根拠 |
|---|---|---|---|
| 1 | EngineError でない例外 | `internal_error` | 例外の型（EngineError の子でない） |
| 2 | StateIntegrityError | `state_integrity` | 例外の型 |
| 3 | UnsupportedError で、コードが互換性の表（compatibility_codes）にある | `compatibility` | コード |
| 4 | IllegalActionError・DeckValidationError（INVALID_DECK）・ConventionSetError | `invalid_input` | 例外の型。subkind は、決定への答え（ResolveDecision・TakePrize・PromoteActive・ReportJankenResult）なら answer、new_game の前なら setup、ほかは command |
| 5 | UnsupportedError・HALTED の halt.code・デッキの検査の UNSUPPORTED_CARD で、台帳の分類が C（または UNRESOLVED_RULING） | `unresolved_ruling` | 台帳の分類（接頭辞だけで決めない） |
| 6 | 同じく、台帳の分類が B | `technical_limit` | 台帳の分類 |
| 7 | 同じく、台帳の分類が A・E（UNSUPPORTED_CARD を含む） | `unsupported` | 台帳の分類 |
| 8 | EngineError で、コード表にないコード、または表の行の例外の型の区分（raised_as）と合わない | `unmapped` | v0.152 の採用（推測で分類しない）。コード表は台帳と台帳の外のコード（不正な操作・状態の不整合など）を合わせたもので、台帳には加えない |

互換性の表（compatibility_codes）: `UNSUPPORTED_CONVENTION_SET`、`UNSUPPORTED_DECISION`、`UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN`
<!-- generated:classification-rules end -->

- 例外の名前の文字列だけでは決めません。`UnsupportedError` は、未裁定（UNRESOLVED_ の研究上の停止）・未対応・技術的制限（`UNSUPPORTED_PREFLIGHT_LIMIT` など）・互換性（`UNSUPPORTED_CONVENTION_SET`・`UNSUPPORTED_DECISION`）を同じ型で表すからです。区別は、停止の方針の台帳の分類（A エンジン機能不足・B 技術的制限・C 公式情報から未裁定・E 内部ガードなど）と止め方から決めます。台帳は「接頭辞だけで公式の不存在を証明しない」と書いており、分類もコードの接頭辞では決めません
- 台帳の実行時の停止コード（`runtime_stop_code`）は、分類 A が 34・B が 5・E が 3（うち 1 つは履歴だけ）、研究上の停止コード（`research_stop_code`）316 はどれも C です（基点の台帳）。B の 5 つ（`UNSUPPORTED_BERRY_ORDER_LIMIT`・`UNSUPPORTED_COLOR_READINGS_LIMIT`・`UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`・`UNSUPPORTED_PREFLIGHT_LIMIT`・`UNSUPPORTED_SECRET_PLAN_IDENTITIES`）は技術的制限です。E の `UNRESOLVED_RULING` は事例を持たない共通の既定のコードなので、未裁定として扱い、事例は `not_identified` にします。E の `UNSUPPORTED_CARD` はデッキの検査の問題の文の中だけにあり、例外のコードとしては投げません（v0.152 のコード表には入れず、デッキの拒否は `INVALID_DECK`）
- 互換性の 3 つのコードは、台帳では分類 A ですが、「この実装がその状態を扱えない」意味なので互換性に分けます（表の `compatibility_codes`）
- 内部エラーは最初の規則で決めます。EngineError でない例外を、未対応・未裁定に変換しません。今のエンジンの `except` は不変条件の確かめの中だけで（`engine.py` の `_bench_limit_or_default` など）、内部エラーを `UnsupportedError` に変える経路は見つかりませんでした
- `new_game` は、負の seed に `ValueError`、整数でない seed に `TypeError` を投げます（EngineError ではない）。このまま規則 1 に当てると内部エラーになるので、アダプタ（U2）が `new_game` の前に入力を確かめ、`invalid_input`（`setup`）にします。エンジンの例外を書き換えるのではありません
- v0.152 の採用: コード表（`kyuura_engine/data/diagnostic_catalog.json`。`scripts/build_diagnostic_catalog.py` が台帳・場面の索引・エンジンのソースから作る）にないコードと、表の行の例外の型の区分と合わない例外は、推測で未裁定・未対応にせず、診断の対応漏れ（`unmapped`）にします。元のコードは検証者用の記録だけに置きます。コード表は、停止の方針の台帳の停止コードと、台帳の外のコード（不正な操作・状態の不整合・デッキの検査・規約集合の構成）を合わせたもので、台帳には加えません。上の規則 8 の前の案（台帳にないコードを `unsupported` にする）は採らなかった

事例 ID: 台帳の事例（`コード#事例`。基点で 9 コード・20 事例）と同梱の場面の索引の場面 ID を使います。今の例外は事例を持たないので、事例を特定できるのは、そのコードの場面が 1 つのときと、続行規約の照会（`conventions.continuation_lookup`）で事例を渡す場所だけです。特定できなければ `case_status` を `not_identified` にします（`ContinuationLookup` の語彙と同じ）。例外に事例を持たせることは、エンジンの変更なので U1 の範囲の外です（必要なら別の判断）。

### 4.4 結果・状態・処理段階

<!-- generated:outcomes begin -->
| 結果 | 意味 | 状態 | 分類 | 次 |
|---|---|---|---|---|
| `accepted` | 操作を受け付けた。新しい状態に置きかわる（乱数・ログが進むことがある） | new |  | 結果の status による（in_progress・awaiting_decision・halted・game_over・sudden_death_pending） |
| `rejected` | 操作を拒否し、元の状態を保った（状態・乱数・ログは変わらない） | kept | invalid_input, unresolved_ruling, unsupported, technical_limit, compatibility, unmapped | 同じ状態に別の操作を送れる（compatibility なら、この実装ではどの操作も同じ拒否）。同じ操作は同じ拒否になる |
| `failed` | 処理できなかった。元の状態で続けることを保証しない | untrusted | state_integrity, internal_error | 対戦を止め、検証者が調べる（自動で続けない） |

| status | 意味 |
|---|---|
| `in_progress` | 番のプレイヤーの操作を待つ（準備の段階を含む） |
| `awaiting_decision` | 決定への答えを待つ（決定の id・種類・決めるプレイヤー・選ぶ数は全員に見え、選べるものは決めるプレイヤーだけ） |
| `halted` | 操作の結果として停止した（終端。halt.code は全員に見え、途中停止なら interruption の公開の記録がある。再開の API はない） |
| `game_over` | 勝ち負けが決まった（終端） |
| `sudden_death_pending` | サドン・デスに移り、延長戦を始める操作（StartSuddenDeath）だけを受け付ける |
| `not_started` | 対戦を始める前の拒否（start_game。状態はない。v0.152） |
| `unavailable` | 処理できなかった結果（failed）。状態を返さない（v0.152） |

| stage | 意味 |
|---|---|
| `setup` | new_game・準備（切り直し・ポケモンを出す・ジャンケン） |
| `turn_action` | 番の操作の宣言（ワザ・トレーナー・特殊能力・にげる・エネルギー・番の終わりなど）の受付と、宣言の前の先読み（v0.152 の名前。仕様案の action_declaration・between_turns をまとめた） |
| `decision_answer` | 保留中の決定への答え（決定の種類・処理の段階は決定の kind と、本人に見える context から） |
| `segment_start` | サドン・デスの延長戦を始める操作 |
| `state_check` | 観測・コマンドの前の状態の確かめ（規約集合・再開先）。将来のスナップショットの復元もここ |
| `submission` | ホストが確かめた送り手とコマンドのプレイヤーの照合（v0.152。エンジンを呼ぶ前） |
| `record_check` | 記録の形式・見出し・依存の確かめ（再現の前。U3 以後） |
<!-- generated:outcomes end -->

同じ状態に同じ操作を送ると、同じ結果になります（拒否は乱数を使わず、受理は同じ乱数の続きを使う）。拒否のあとに「やり直し」で得をすることはありませんが、受理のあとに前の状態から操作をやり直すと、コインの結果を見てから選び直せてしまいます。これを防ぐのは、状態を持つ側（5.1 節）の責任です。

### 4.5 診断の項目と安定性

<!-- generated:diagnostic-fields begin -->
| 項目 | 固定か説明用か | 必須 | 渡す相手 | 意味 |
|---|---|---|---|---|
| `kyuura_diagnostic_schema` | fixed | はい | viewer | 診断の形の版（整数。v0.152 は 1） |
| `role` | fixed | はい | viewer | actor（本人への結果）・observer（相手・観戦者への今の状態の知らせ） |
| `viewer` | fixed | はい | viewer | 見る人（0・1・null） |
| `outcome` | fixed | はい | actor | accepted・rejected・failed（本人だけ） |
| `status` | fixed | はい | viewer | 操作のあとの状態（statuses の語彙） |
| `stage` | fixed | はい | actor | 送った操作の処理段階（コマンドの種類と公開の段階から決まる） |
| `continuable` | fixed | はい | viewer | 実際の状態で、この版が次の操作を処理しうるか（分類から推測しない） |
| `next` | fixed | はい | viewer | 次に受け付けうる操作の種類と送るプレイヤー（合法手の一覧ではない） |
| `diagnostic_id` | fixed | はい | actor | API として安定した診断の識別。コード表で対応付けたコードはそのコード、アダプタが作るものは DIAGNOSTIC_UNMAPPED・INTERNAL_ERROR・SUBMITTER_MISMATCH・INVALID_SEED |
| `category` | fixed | はい | actor | 診断の分類（accepted なら null） |
| `subkind` | fixed | いいえ | actor | 不正な入力の区分（command・answer・setup） |
| `case_id` | fixed | いいえ | actor | コードの場面が 1 つのときの事例 ID。2 つ以上なら null |
| `case_status` | fixed | はい | actor | identified・not_identified・not_applicable |
| `message` | explanatory | いいえ | actor | コードに対応する安全な定型文（埋め込みなし。v0.152 の採用）。プログラムで判定しない |
| `halt` | fixed | いいえ | viewer | 停止した状態の公開の診断（識別・分類・事例・停止の定型文・途中停止か） |
| `operation_id` | fixed | いいえ | actor | ホストが付けた操作の識別（将来の記録との対応。本人だけ） |
| `convention_set` | fixed | はい | viewer | 適用中の規約集合の ID・版・照合値 |
| `engine_code` | fixed | いいえ | verifier | エンジンが返した元のコード（対応漏れのときも） |
| `raw_message` | explanatory | いいえ | verifier | 例外の生の文 |
| `traceback` | explanatory | いいえ | verifier | 例外の traceback |
| `problems` | explanatory | いいえ | verifier | 状態の不整合の問題の文 |
| `halt_message` | explanatory | いいえ | verifier | 停止の診断用の文・references |
| `command` | explanatory | いいえ | verifier | 送ったコマンド（command_to_dict） |
<!-- generated:diagnostic-fields end -->

API として固定するもの（`fixed`）と、説明用で版によって変わりうるもの（`explanatory`）を分けます。

- **固定**: 分類・結果・status・処理段階の語彙、`code`、事例 ID、`ref`、規約集合の識別。エンジンのコードは定数か文字列で、台帳がすべてを追っています。v0.151 の修正のように、止める条件や理由の文を変えてもコードは変えてきませんでした。この慣行を約束にします: 一度出したコードの意味を変えず、使わなくなったコードは台帳に `historical` として残し、別の意味に使い直しません
- **説明用**: `message`（理由の文）。v0.151 では、はらだいこなどの理由の文を決まった文に変えました。同じコードでも文は版で変わります。プログラムは文で判定しないでください。lockstep が文の指紋を比べているのは同じ版どうしの比べのためで、文の固定の約束ではありません

## 5. 情報境界

### 5.1 権限と信頼境界

<!-- generated:roles begin -->
| 権限 | 意味 | 持つもの |
|---|---|---|
| `actor` | 操作する本人（決定への答えなら決めるプレイヤー） | プレイヤーの画面・AI。状態を持たない |
| `opponent` | 相手のプレイヤー | プレイヤーの画面・AI。状態を持たない |
| `spectator` | 観戦者（observe の viewer=None） | 観戦の画面。状態を持たない |
| `verifier` | 完全な情報を扱う検証者（開発・不具合調査・審判役） | 状態・完全な記録を持つ側（対戦を進める権限の側か、その写しを受け取った調査の環境）。見る人の値ではなく、完全な状態を持っていることが権限 |
<!-- generated:roles end -->

エンジンはライブラリで、認証やアクセス制御をしません。**`GameState`（完全な状態）を持っている側が、すべての情報を持っています。** そのため、権限は次のように分けます。

- 見る人の値は、今の `observe` と同じ 0・1・`None`（観戦者）だけです。検証者を表す値を加えません。「`viewer="verifier"` を渡すと完全な情報が返る」形の API にすると、引数を変えるだけで権限が上がってしまうからです（P-NO-PROMOTION）
- 完全な情報を返す関数（検証者の診断・完全な再現用記録・スナップショット）は、完全な状態か完全な記録を引数に取るものだけにします。それを呼べること自体が、状態を持っている（＝権限がある）ことを意味します
- 対戦を進める権限の側（ローカルの対戦ならそのプロセス、オンラインならサーバー）だけが状態を持ちます。画面・AI・相手・観戦者には、見る人ごとの写し（観測・ログの写し・本人向けの診断）だけを渡します。状態・形式 35 の書き出し・pickle・完全な記録をプレイヤーの側に渡すと、そこで情報境界は失われます
- だれが検証者かを決めること（調査の担当者・審判役の認証、記録の保管場所の権限）は、ホストするアプリケーションの責任です。この仕様は、どの値が検証者だけのものかを決めます

### 5.2 項目ごとの見える範囲

値の語彙: `yes` 見える、`no` 見えない、`own` 本人に関わるものだけ（自分の操作・自分のデッキリスト）、`decider` 決めるプレイヤーだけ、`derived` 観測・ログの写しを通した形だけ。

<!-- generated:visibility begin -->
| 項目 | 群 | 本人 | 相手 | 観戦者 | 検証者 | 根拠 |
|---|---|---|---|---|---|---|
| diagnostic.outcome（拒否された操作） | diagnostic | yes | no | no | yes | 拒否は状態を変えずログにも残らない。相手に試した操作を知らせない（本人の手札などを含む操作の内容が漏れる） |
| diagnostic.category・code・subkind・stage | diagnostic | yes | no | no | yes | 受理・拒否と同じ境界（v0.135〜v0.151 の双子の比較の対象） |
| diagnostic.case_id | diagnostic | yes | no | no | yes | 事例は止まった場所（コードの区別）で決まり、秘密の配分で決めない。配分で事例が変わる場所は事例を出さない（not_identified） |
| diagnostic.message | diagnostic | yes | no | no | yes | コードに対応する安全な定型文だけ（v0.152 の採用。D-MESSAGE）。生の文は検証者用 |
| diagnostic.developer_detail・detail_ref | diagnostic | no | no | no | yes | 例外の生の文・halt.message・解決の記録は実際の配分を含みうる |
| halt.code（停止した状態） | diagnostic | yes | yes | yes | yes | ログ halted と同じ（全員に見えるイベント） |
| halt.message・references | diagnostic | no | no | no | yes | 診断用の文（観測に入らない） |
| interruption の公開の記録 | diagnostic | yes | yes | yes | yes | interruption.public_record（全員に見える項目だけ） |
| internal_error の分類 | diagnostic | yes | yes | yes | yes | 対戦が止まったことは全員に分かる。内容は検証者だけ |
| decision.id・kind・player・選ぶ数 | decision | yes | yes | yes | yes | observation._decision と同じ |
| decision.options（選べるもの） | decision | decider | decider | no | yes | 決めるプレイヤーにだけ（見えるカードにだけ id を添える） |
| decision.resume・context | decision | no | no | no | yes | 内部の続きの情報 |
| 受理した操作（コマンドそのもの） | record | own | derived | derived | yes | 選んだ値に山札・手札のカードの uid が入りうる。ほかの人にはログの写し（visible_log）で見せる |
| 拒否された操作の列 | record | own | no | no | yes | 診断と同じ |
| ログ（イベント） | record | derived | derived | derived | yes | visible_log・visible_segment_logs の写し（PRIVATE_FIELDS の見える人） |
| コインの結果 | record | yes | yes | yes | yes | 投げたあとのログ coin_flip（全員）。再現の入力にはしない（seed から決まる確認値） |
| デッキリスト | record | own | no | no | yes | 持ち主は自分で出したので知っている。相手のデッキリストは公開されない（対戦後の公開は D-POSTGAME） |
| 初期の山札の並び・サイドの中身 | record | no | no | no | yes | 見えない情報（並びから未来に引くカードが分かる） |
| seed | record | no | no | no | yes | ログ game_created の seed はだれにも見せない（_nobody）。seed から山札の並び・コインが分かる |
| 乱数の状態・乱数の指紋（rng_state_sha256） | record | no | no | no | yes | 指紋でも、小さな seed を総当たりで確かめて未来のコイン・山札を予測できる |
| 完全な状態の指紋（形式 35 の sha256） | record | no | no | no | yes | 見えない配分の候補を当てはめて指紋と比べれば、推測を確かめられる（サイドの中身など、候補の少ない秘密） |
| 完全な状態・形式 35 の書き出し・pickle | record | no | no | no | yes | 内部の完全な記録（observation の説明） |
| 規約集合の識別 | record | yes | yes | yes | yes | observe の convention_set（全員に見える） |
| エンジンの版・実装の識別 | record | yes | yes | yes | yes | 秘密の情報を含まない。両方が同じ実装で対戦していることを確かめられる |
| 区間の結果・番号・サイドの枚数 | record | yes | yes | yes | yes | observe の segment（全員） |
| AI・道具の方策の名前と方策用の種 | record | own | no | no | yes | エンジンの乱数とは別。再現の入力にしない（参考の記録）。相手に渡すと方策の手を予測できる |
<!-- generated:visibility end -->

指紋の扱いに注意してください。乱数の指紋や完全な状態の指紋は、ハッシュなので中身は読めません。しかし、候補の少ない秘密（seed は小さな整数のことが多い。サイドの中身の候補は限られる）なら、候補を当てはめて指紋と比べるだけで推測を確かめられます。形式 35 の書き出しは `seed` と `rng_state_sha256` を含み、lockstep の記録は状態の指紋を歩ごとに持ちます。どちらも検証者だけのものです。

### 5.3 約束

<!-- generated:principles begin -->
| ID | 約束 | 由来 | 確かめ |
|---|---|---|---|
| P-REJECT-SPLIT | 受理・拒否・診断の分類・コード・事例・本人への文は、秘密の領域（山札・うらのサイド・見えない置いておくカード）への配分で変わらない | v0.135〜v0.151（双子の比較） | U1・U2 の回帰テストで、診断の写しを twin_command_problems で比べる |
| P-PRESEARCH | 山札をさがす前の診断は、本人の知る情報（山札にあるかもしれないカード・配分を読まない下限・公開の枚数）だけで作る | v0.147・v0.148・v0.151 | 診断を作る関数は、確かめの関数が返した結果だけを使い、実際の山札を読み直さない |
| P-POSTSEARCH | さがし始めたあとに本人が正当に見た山札の内容（決定の選べるもの・見たカード）は、本人の診断・決定に使える | v0.150・v0.151 | 決定の選べるものの見える範囲は observation._decision に従う |
| P-DEV-DETAIL | 開発用の詳細（生の文・halt.message・解決の記録・実装の場所）は検証者だけに渡し、相手・観戦者に送らない | この仕様 | 閲覧用の診断・記録の写しに developer_detail の項目がない（--check と U1 のテスト） |
| P-FULL-NOT-VIEW | 完全な状態・形式 35・完全な記録・スナップショットを、表示用の観測と混同しない（見る人に渡さない） | v0.47 の観測の約束 | 閲覧用記録は観測・ログの写しだけから作る |
| P-NO-RECONSTRUCT | 閲覧用記録から完全な再現用記録を復元できるとは保証しない（復元できないことを目標にする） | この仕様 | 閲覧用記録に seed・乱数・状態の指紋・相手のコマンドを入れない |
| P-NO-PREDICT | 未来の見えない情報を予測できる値（seed・乱数の状態とその指紋・完全な状態の指紋・初期の山札の並び）を、検証者のほかに配らない | この仕様 | visibility の表で検証者だけ（--check） |
| P-NO-FREE-REDO | 対戦を進める権限の側だけが状態を持つ。見る人は状態を持たず、コインの結果・見た秘密のあとで前の状態から操作をやり直せない | apply_command が渡した状態を変えないことの裏側（v0.151 の「見たあとのやり直しをさせない」） | アダプタは古い状態への操作を受け付けない（U2 の完了基準） |
| P-NO-PROMOTION | 権限を引数で指定するだけで完全な情報に上がる API にしない（見る人の値に verifier を加えない） | この仕様 | 完全な情報を返す関数は、完全な状態・完全な記録を引数に取るものだけ。見る人の値は 0・1・None のまま |
| P-INTERNAL-NOT-UNSUPPORTED | 内部エラーを未対応・未裁定に変換しない | この仕様 | 分類の規則の 1 番目（--check と U1 のテスト） |
<!-- generated:principles end -->

本人に返す理由の文（`message`）について: v0.135〜v0.151 で双子の比較で確かめたのは、対象群（クイズの答え、山札をさがす効果の使う前の確かめ・先読み・決定の有無・研究上の停止など）の受理・拒否と文です。そのほかの拒否の文が配分によらないことは、まだ確かめていません。そのため、文は本人と検証者だけに返し（相手・観戦者には送らない）、プログラムは `code` で判定する形を推奨します（判断事項 D-MESSAGE）。

v0.152 の採用: 本人向けの説明は、エンジンの生の文ではなく、コードに対応する安全な定型文（コード表の文。カード名・uid・枚数を埋め込まない）にしました。生の例外文・traceback・停止の診断用の文は、検証者用の記録（`VerifierReport`）だけに置きます。上の推奨（生の文を本人に返す）は採りませんでした。

## 6. 記録の種類

3 つの記録は用途も持つ側も違うので、1 つのデータ構造にまとめません。共通なのは識別の見出しだけです。

<!-- generated:records begin -->
#### A. 完全な再現用記録（v0.153 で実装）（`kyuura_replay_format`）

- 用途: 不具合調査・検証・同一実行の再現
- 持つ側: 検証者（対戦を進める権限の側）
- 秘密の情報を含む: はい
- 再現の入力: header.initial、header.engine（扱えるかの条件）、header.runtime（扱えるかの条件）、header.dependencies、header.convention_set、operations[].command（outcome が accepted のもの、accepted_index の順）
- 確認値: header.start.check、operations[].outcome・diagnostic・status、operations[].check、end
- 保証: 構造の検証（形・順序・前後の矛盾・完結・扱える範囲）。再実行して確認値と一致すること（同一実行の再現）は U4 で確かめる
- 保証しない: 実装・依存・規約集合・Python の実装と版が違うときの再現（比べは compare_runs の別の機能）。seed だけからの、版をまたぐ再現。方策の再実行で同じ操作の列になること。閉じた記録・停止した記録からの対戦の再開

| 項目 | 必須 | 役割 | 意味 |
|---|---|---|---|
| `kyuura_replay_format` | はい | format | 記録の形式の版（整数。状態の形式・lockstep の record_format とは別の番号） |
| `header.engine` | はい | input | エンジンの版と実装の識別（behavior_digest: 挙動に関係するソース・同梱データ、instrumentation_digest: 記録・診断の部品）。git_commit は補助の情報 |
| `header.runtime` | はい | environment | Python の実装と版・乱数の方式（rng.RNG_FORMAT と getstate の版）。OS・パスは入れない |
| `header.dependencies` | はい | input | ルールの組の id・カードプール（default だけ）・カードデータの写しの元・効果の登録表の id |
| `header.convention_set` | はい | input | ConventionSetIdentity.record（ID・版・照合値・構成） |
| `header.formats` | はい | reference | 参照する形式: 状態の書き出しの形式（35）・確認値の方式・診断の形式 |
| `header.initial` | はい | input | デッキリスト 2 つ・seed・ルールの組・規約集合・カードプール（new_game の入力。先攻はジャンケンの結果の操作として操作の列に入る） |
| `header.start` | はい | expected | new_game の結果の status と確認値 |
| `header.game_id・rejections_recorded` | はい | reference | 対戦の識別（任意）と、拒否した操作を記録したか |
| `operations[].seq・accepted_index` | はい | reference | 記録の中の連番（1 から欠けなし）と、受理した操作の中の順（拒否を省いても受理の順が決まる）。operation_id（ホストが付ける）とは別 |
| `operations[].actor・submitter・segment` | はい | reference | 結果を受けるプレイヤー・ホストが確かめた送り手・操作の前の区間 |
| `operations[].command` | はい | input | command_to_dict の形。受理したものだけが再現の入力 |
| `operations[].answers_decision` | いいえ | reference | 答えた決定の id（決定への答えのとき） |
| `operations[].outcome・status・diagnostic` | はい | expected | accepted・rejected・failed と、操作のあとの status、拒否・失敗の診断の識別・分類・元のコード（生の文は入れない） |
| `operations[].check` | いいえ | expected | 受理した操作のあとの確認値（状態の指紋・乱数の指紋・ログの長さ・区間・status・決定・停止のコード）。受理したものだけ（D-CHECK-DENSITY） |
| `end` | はい | expected | 記録の終わり: closed（ホストが閉じた）・aborted（処理できない結果で止めた）、操作の数・受理の数・status・最後の確認値・区間の境界。ないなら途中で切れた記録 |

#### B. 本人・相手・観戦者向けの閲覧用記録（`kyuura_view_format`）

- 用途: 画面の表示・対戦の履歴・共有
- 持つ側: 見る人（プレイヤー・観戦者）
- 秘密の情報を含む: いいえ
- 再現の入力: なし
- 確認値: なし
- 保証: その見る人が対戦中に観測・ログの写しで見たものと同じ（収集した時点の値で固定）
- 保証しない: 完全な再現用記録・スナップショットの復元・閲覧用記録からの再実行。ほかの見る人の記録の作り直し。手で作った記録の内容が安全な投影から作られたこと（構造の検証は認証ではない）

| 項目 | 必須 | 役割 | 意味 |
|---|---|---|---|
| `kyuura_view_format` | はい | format | 閲覧用記録の形式の版（再現用記録の形式とは別の番号。v0.155 は 1） |
| `header.viewer・role・origin` | はい | reference | 閲覧者（0・1・観戦者。作るときに固定）・player か spectator・記録の始まり（new_game か、途中から始めた attached） |
| `header.engine_version・convention_set・diagnostic_schema` | はい | reference | エンジンの版・規約集合の識別（ID・版・照合値）・診断の形式（全員に見える値） |
| `header.own_decklist` | はい | reference | プレイヤーの記録だけ。自分のデッキのカードの組（並びではない）。観戦者は null |
| `entries[].n・kind・segment` | はい | reference | その閲覧者の記録に出した項目だけで連続する番号・種類（start・update・own_rejection・unavailable）・区間 |
| `entries[].events` | いいえ | reference | その時点の閲覧用ログの新しいイベント（区間の番号・ログの位置・イベント）。あとで遡って変えない |
| `entries[].observation` | いいえ | reference | その時点の observe（選べるものは決めるプレイヤーの記録だけ） |
| `entries[].notice` | はい | reference | その時点の view_for（本人は結果と診断、相手・観戦者は状態の知らせ）。operation_id は入れない。拒否は本人の記録だけ |
| `end` | はい | reference | 記録の閉じ方（closed・aborted）・項目の数・最後の status。ないなら途中の記録 |

#### C. 状態スナップショット（`kyuura_snapshot_format`）

- 用途: 将来の JSON の保存・復元による途中再開
- 持つ側: 対戦を進める権限の側
- 秘密の情報を含む: はい
- 再現の入力: state（すべての項目）、rng（rng_state_to_json）
- 確認値: check
- 保証: 同じ実装で復元して続けると、途中で保存しなかった場合と同じ結果になる（U6 で確かめる）
- 保証しない: 実装・規約集合が違う版での復元。前の形式の自動移行。HALTED からの再開

| 項目 | 必須 | 役割 | 意味 |
|---|---|---|---|
| `kyuura_snapshot_format` | はい | format | スナップショットの形式の版（形式 35 とは別の番号） |
| `header.engine・dependencies・convention_set` | はい | input | 再現用記録の見出しと同じ識別 |
| `state` | はい | input | 状態のすべての項目（ログ・区間・決定の resume と context を含む） |
| `rng` | はい | input | 乱数の状態そのもの（rng_state_to_json） |
| `check` | はい | expected | 状態の指紋（復元のあとに同じ値になること） |
| `origin` | いいえ | reference | 作った記録（game_id・歩の番号） |

共通の部分: エンジンの版と実装の識別、規約集合の識別（ConventionSetIdentity.record）、対戦の識別 game_id と区間の番号、知らない形式・項目の拒否
<!-- generated:records end -->

補足:

- **入力と確認値を分けます。** 再現の入力は、見出しの実装と依存・規約集合・初期の条件と、受理した操作の列だけです。コインの結果・状態の指紋・拒否の結果・決定の要約は確認値で、再実行の値と比べるためにだけ使います。コインの結果は seed と操作の列から決まるので、記録のコインを「正」として再実行に流し込みません（コマンドでコインの結果を指定する方法も、今のエンジンにありません）。同じ結果を入力と期待の両方にしません
- **拒否された操作**は、記録しても再現の入力にはしません。再現では「同じ状態に同じ操作を送ると同じ拒否になる」ことを確かめる確認値として使います（判断事項 D-REJECTED）
- **方策を再実行しない**: 記録には、実際に送った操作をそのまま書きます。lockstep の記録はコマンドの指紋だけなので、対戦を作り直すには方策（`play_game`・`choose_command`）を再実行するしかありませんでした。再現用記録は、方策の乱数・方策の版によらずに再現できる形にします
- **サドン・デス**: 延長戦は `StartSuddenDeath` の歩で始まり、区間の番号が 1 つ増えます。エンジンは乱数を前の区間から続けます（seed にもどさない。`engine._start_sudden_death`）。そのため、区間ごとに記録を分けず、1 つの操作の列の中に境界（`segments[]`）を書きます
- **途中で切れた記録**: 終わりの印（`footer`）がない記録は、確かめた歩までを返す `incomplete` にし、成功に数えません。対戦の途中で保存した記録（まだ終わっていない）と、書き込みの途中で壊れた記録は、終わりの印の `reason`（`abandoned` など）の有無で区別します

## 7. 再現インターフェース

<!-- generated:replay begin -->
| 関数 | 意味 | 使う記録 | 返しうる結果 |
|---|---|---|---|
| `replay_from_start` | 記録の見出しの初期の条件から new_game を作り、記録の行を seq の順に（拒否・失敗の行も）送り直す（方策を再実行しない。v0.154 で replay_run.replay として実装。v0.153 までの「受理した操作を順に」は seq の順に訂正した） | replay_full | succeeded, incomplete, recorded_failure, unsupported, invalid_record, diverged, internal_error |
| `verify_record` | 記録の形・見出し・依存を確かめ、再実行して各歩の確認値（受理・拒否・コード・状態の指紋・コイン・決定）と比べる。ログの監査は追加の確かめ | replay_full | succeeded, incomplete, recorded_failure, unsupported, invalid_record, diverged, internal_error |
| `resume_from_snapshot` | スナップショットを復元し、確かめ（不変条件・規約集合・再開先）を通してから続きの操作を送る | snapshot, replay_full | succeeded, unsupported, invalid_record, diverged, internal_error |
| `compare_runs` | 異なる版・規約集合の 2 つの記録を、同じ初期の条件・同じ操作の列で比べ、最初の差を返す（同一実行の再現とは別。成功を返さない） | replay_full | unsupported, invalid_record, diverged, internal_error |

| 結果 | 意味 |
|---|---|
| `succeeded` | 最後まで確認値と同じ（記録が完全） |
| `incomplete` | 終わりの印のない記録で、ある歩までは同じ（どこまで確かめたかを返す。成功に数えない） |
| `recorded_failure` | aborted の記録で、失敗の行まで同じで、同じ失敗がもう一度起きた（失敗を含む結果。成功に数えない。v0.154） |
| `unsupported` | 記録の形式の版・実装・依存・規約集合・実行環境を、この実装が扱えない（理由の項目を返す） |
| `invalid_record` | 記録の形が不正・項目が足りない・見出しと歩が合わない・番号が飛ぶ |
| `diverged` | 最初に違った歩（区間・番号・操作）と比較項目（outcome・code・state_digest・coins・decision・status・log_length）と、記録の値・再実行の値 |
| `internal_error` | 再実行の中の内部エラー（diverged に変えない） |

保証の範囲（すべて同じとき）: 実装の識別（implementation_digest）、依存のデータ（カードデータの照合値・効果の登録表の id・ルールの組）、規約集合（ID・版・照合値）、初期の条件（デッキリスト・seed・乱数の方式）、受理した操作の列

- 乱数: エンジンの乱数は state.rng の 1 本だけ（rng.py）。AI・道具が操作を選ぶ乱数は別で、記録の入力にしない（送った操作そのものを記録する）
- コイン: コインの結果は入力ではない（seed と操作の列から決まる）。記録のコインは確認値で、再実行の値と違えば diverged。同じ結果を入力と期待の両方として扱わない
- 版をまたぐ比べ: seed だけで版をまたぐ再現を保証しない。版・規約集合が違う比べは compare_runs で、結果は差の報告
<!-- generated:replay end -->

- 最初の保証の範囲は、同じ実装・同じ依存データ・同じ規約集合・同じ初期の条件・同じ操作の列です。これは api-review 1 章の「デッキ 2 つ・seed・コマンドの列」に、実装・依存・規約集合の識別を加えたものです
- エンジンの乱数は `state.rng` の 1 本だけです。AI や対戦の道具が操作を選ぶ乱数（`tools/stress_engine.py` などの `random.Random`）は別のもので、記録の入力にしません
- 異なる版・規約集合の比べ（`compare_runs`）は、lockstep の `--cross-set` と同じく、同一実行の再現とは別の機能です。最初の差を報告するだけで、「互換」とは判定しません
- 内部エラーは `diverged` に変えず、`internal_error` として返します

## 8. 版と互換性

<!-- generated:versions begin -->
| 版の項目 | 状態 | 持ち主 | 変わるとき | 注 |
|---|---|---|---|---|
| `engine_version` | existing | kyuura_engine.__version__ | エンジンの版ごと（処理の実装） | 同じ版の番号に複数のコミットがある。実装の識別には足りない（D-IMPLEMENTATION-ID） |
| `convention set version` | existing | conventions.ConventionSetIdentity（集合 ID@版・照合値） | 集合の中身の意味が変わるとき | 同じ ID・版の中身は変えない（固定した照合値で確かめる） |
| `format_version` | existing | serialize.FORMAT_VERSIONS（1〜35） | 書き出しの形が変わるとき（値の語彙を足すだけなら変えない） | 一方向の書き出し。スナップショットの形式と別の番号にする |
| `record_format` | existing | tools/engine_lockstep.py（1・2） | 道具の記録の形が変わるとき | 検証用の道具の形式。再現用記録の形式として読み替えない |
| `kyuura_diagnostic_schema` | proposed | 診断の型（U1） | 診断の項目の形・分類の語彙が変わるとき | 1 から |
| `kyuura_replay_format` | proposed | 完全な再現用記録（U3） | 記録の形が変わるとき | 1 から（v0.153 で実装） |
| `kyuura_view_format` | proposed | 閲覧用記録（U5） | 閲覧用記録の形が変わるとき | 1 から（v0.155 で実装。再現用記録とは別の番号。診断の形式は header.diagnostic_schema で参照する） |
| `kyuura_snapshot_format` | proposed | 状態スナップショット（U6） | スナップショットの形が変わるとき | 1 から |

- 知らない形式の版・知らない項目・知らない値（決定の種類・再開先・イベントの種類・持続する効果の種類）は拒否する（compatibility）。形式の番号が同じでも、前の版の読む側が後の版の書き出しを読めるとは約束しない（serialize の互換性の約束と同じ）
- 知らない決定（この版が知らない再開先・前の版の決定）を待つ状態は、UNSUPPORTED_DECISION で拒否する（v0.140 の入口をそのまま使う）
- 対応しない規約集合（登録と内容が違う・知らない ID・版）は UNSUPPORTED_CONVENTION_SET で拒否する
- 古い記録・形式 35 の書き出し・lockstep の記録を、スナップショットや再現用記録として黙って読み替えない（項目の名前が別なので、形で区別できる）
- 旧記録の自動移行と、すべての過去の版への対応は前提にしない（必要なら移行の道具を別に作り、移行したことを記録に書く）
- 実装の識別が違う記録の再現は unsupported を返す（seed が同じでも）。比べたいときは compare_runs
<!-- generated:versions end -->

版を分ける理由と、増やしすぎない方法:

- エンジンの版（処理の実装）と規約集合の版（未決の場面の扱いの意味）は、v0.142 で分けてあります。不具合の修正はエンジンの版だけを変え、規約集合の版は変えません
- 状態の書き出しの形式（1〜35）は**一方向の書き出しの形**の版で、読み込みの形式ではありません。スナップショットは別の番号（`kyuura_snapshot_format`）にします。形式 35 の書き出しを、読み込み用に黙って読み替えません。形式 35 が状態を落とさず表すかは確かめていないので、スナップショットの元にするかは U6 の監査のあとで決めます（D-SNAPSHOT-BASE）
- lockstep の記録の形式（`record_format` 1・2）は検証用の道具の形式です。再現用記録（`kyuura_replay_format`）とは項目の名前が違うので、形で区別できます。どちらも、もう一方として読みません
- 新しい版は、どれも整数 1 つで、形が変わったときだけ上げます。値の語彙を足すだけでは上げません（`serialize` の互換性の約束と同じ）。読む側は、知らない版・項目・値を拒否します。そのため、版の番号が同じでも、前の実装が後の実装の記録を読めるとは約束しません
- 旧記録の自動移行と、すべての過去の版への対応は前提にしません

## 9. 具体例

ここの例は、**未実装の API の形の例示**です。実在の関数の出力ではありません。`<照合値>`・`<sha256>` などは値の置き場所で、実際の値ではありません。コードと事例 ID は、実在のもの（エンジンのソース・台帳・場面の索引にあるもの）だけを使っています（`--check` が確かめます）。

<!-- generated:examples begin -->
#### EX1-ACCEPTED: 通常の操作の成功（`api_status`: illustrative）

番のプレイヤー 0 が手札の基本エネルギーカードをバトル場のポケモンにつける

```json
{
 "kyuura_diagnostic_schema": 1,
 "outcome": "accepted",
 "category": null,
 "diagnostic_id": null,
 "case_id": null,
 "case_status": null,
 "stage": "turn_action",
 "status": "in_progress",
 "continuable": true,
 "next": [
  {
   "kind": "turn_action",
   "player": 0
  }
 ],
 "ref": {
  "game_id": "g-0001",
  "segment": 0,
  "step": 12,
  "decision_id": null
 },
 "convention_set": {
  "id": "CS-KYUURA-CURRENT",
  "version": 1,
  "digest": "<照合値>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "outcome": "accepted",
  "status": "in_progress"
 },
 "opponent": {
  "events": [
   "attach_energy"
  ]
 },
 "spectator": {
  "events": [
   "attach_energy"
  ]
 }
}
```

#### EX2-ILLEGAL: 不正な操作による拒否（`api_status`: illustrative）

番でないプレイヤー 1 が番の終わりを送る

```json
{
 "kyuura_diagnostic_schema": 1,
 "outcome": "rejected",
 "category": "invalid_input",
 "subkind": "command",
 "diagnostic_id": "NOT_YOUR_TURN",
 "case_id": null,
 "case_status": "not_applicable",
 "stage": "turn_action",
 "status": "in_progress",
 "continuable": true,
 "next": [
  {
   "kind": "turn_action",
   "player": 0
  }
 ],
 "message": "今はあなたの番ではありません。",
 "ref": {
  "game_id": "g-0001",
  "segment": 0,
  "step": 13,
  "decision_id": null
 },
 "convention_set": {
  "id": "CS-KYUURA-CURRENT",
  "version": 1,
  "digest": "<照合値>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "outcome": "rejected",
  "category": "invalid_input",
  "diagnostic_id": "NOT_YOUR_TURN"
 },
 "opponent": null,
 "spectator": null
}
```

#### EX3-UNRESOLVED: 未裁定での停止（宣言の拒否）（`api_status`: illustrative）

はらだいこを宣言したが、配分を読まない下限が 2 より小さく、山札に基本エネルギーカードがあるかもしれない（v0.151 の保守的な停止）

```json
{
 "kyuura_diagnostic_schema": 1,
 "outcome": "rejected",
 "category": "unresolved_ruling",
 "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT",
 "case_id": null,
 "case_status": "not_identified",
 "stage": "turn_action",
 "status": "in_progress",
 "continuable": true,
 "next": [
  {
   "kind": "turn_action",
   "player": 0
  }
 ],
 "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンはこの操作を受け付けません。",
 "ref": {
  "game_id": "g-0002",
  "segment": 0,
  "step": 40,
  "decision_id": null
 },
 "convention_set": {
  "id": "CS-KYUURA-CURRENT",
  "version": 1,
  "digest": "<照合値>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "outcome": "rejected",
  "category": "unresolved_ruling",
  "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT",
  "case_status": "not_identified"
 },
 "opponent": null,
 "spectator": null
}
```

#### EX4-LIMIT: 技術的上限による非対応（`api_status`: illustrative）

相手のうらのカード（マチスの秘策）を 2 枚以上指定する操作で、受け付けるかを本当のカードによらず確かめる回数の上限を超える

```json
{
 "kyuura_diagnostic_schema": 1,
 "outcome": "rejected",
 "category": "technical_limit",
 "diagnostic_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES",
 "case_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES",
 "case_status": "identified",
 "stage": "turn_action",
 "status": "in_progress",
 "continuable": true,
 "next": [
  {
   "kind": "turn_action",
   "player": 0
  }
 ],
 "ref": {
  "game_id": "g-0003",
  "segment": 0,
  "step": 21,
  "decision_id": null
 },
 "convention_set": {
  "id": "CS-KYUURA-CURRENT",
  "version": 1,
  "digest": "<照合値>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "outcome": "rejected",
  "category": "technical_limit",
  "diagnostic_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES"
 },
 "opponent": null,
 "spectator": null
}
```

#### EX5-DEV-VS-SAFE: 秘密情報を含む開発用診断と、安全な閲覧者向け診断（`api_status`: illustrative）

EX3 と同じ拒否。検証者の詳細には実際の山札の枚数・解決の記録が入りうるが、本人には決まった文、相手・観戦者には何も送らない

```json
{
 "verifier": {
  "mapped": true,
  "engine_code": "UNRESOLVED_STATED_CARDS_SHORT",
  "exception_type": "UnsupportedError",
  "raw_message": "<例外の生の文>",
  "traceback": "<traceback>",
  "command": {
   "type": "use_attack",
   "player": 0,
   "attack": 0
  },
  "developer_detail": {
   "trace": "<apply_command_traced の解決の記録（v0.152 では作らない）>",
   "secret_note": "実際の山札の基本エネルギーカード 3 枚・うらのサイド 4 枚（例示）"
  }
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "outcome": "rejected",
  "category": "unresolved_ruling",
  "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT",
  "message": "<コードに対応する定型文>"
 },
 "opponent": null,
 "spectator": null
}
```

#### EX6-DECISION-RECORD: 決定待ちを含む再現用記録（`api_status`: illustrative）

パソコン通信で山札をさがす決定が出て、次の歩で答える（記録は検証者だけ）

```json
{
 "kyuura_replay_format": 1,
 "header": {
  "engine": {
   "version": "0.151.0",
   "implementation_digest": "<sha256>"
  },
  "runtime": {
   "python": "CPython 3.14.6"
  },
  "dependencies": {
   "rules": "<RuleSet.id>",
   "card_data": {
    "commit": "<kyuura の commit>",
    "digest": "<sha256>"
   },
   "effects": "<登録表の id>"
  },
  "convention_set": {
   "id": "CS-KYUURA-CURRENT",
   "version": 1,
   "digest": "<照合値>"
  },
  "initial": {
   "decklists": [
    "<60 枚>",
    "<60 枚>"
   ],
   "seed": 7,
   "rng": "python-random-mt19937-v3"
  },
  "game_id": "g-0004"
 },
 "steps": [
  {
   "index": 30,
   "segment": 0,
   "actor": 0,
   "command": {
    "type": "play_trainer",
    "player": 0,
    "card": 17
   },
   "outcome": {
    "result": "accepted"
   },
   "check": {
    "state_digest": "<sha256>",
    "log_length": 211,
    "status": "awaiting_decision",
    "decision": {
     "id": 9,
     "kind": "search_deck"
    }
   }
  },
  {
   "index": 31,
   "segment": 0,
   "actor": 0,
   "decision_id": 9,
   "command": {
    "type": "resolve_decision",
    "player": 0,
    "decision": 9,
    "choices": [
     42
    ]
   },
   "outcome": {
    "result": "accepted"
   },
   "check": {
    "state_digest": "<sha256>",
    "log_length": 215,
    "status": "in_progress",
    "decision": null
   }
  }
 ],
 "footer": null
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "opponent": {
  "decision": {
   "id": 9,
   "kind": "search_deck",
   "player": 0,
   "options": null
  }
 }
}
```

#### EX7-SUDDEN-DEATH: サドン・デスの区間を含む記録（`api_status`: illustrative）

同時のきぜつでサドン・デスに移り、StartSuddenDeath で延長戦（サイド 1 枚）を始め、延長戦で勝ちが決まる

```json
{
 "kyuura_replay_format": 1,
 "steps": [
  {
   "index": 88,
   "segment": 0,
   "actor": 1,
   "command": {
    "type": "use_attack",
    "player": 1,
    "attack": 0
   },
   "outcome": {
    "result": "accepted"
   },
   "check": {
    "status": "sudden_death_pending"
   }
  },
  {
   "index": 89,
   "segment": 0,
   "actor": 0,
   "command": {
    "type": "start_sudden_death",
    "player": 0
   },
   "outcome": {
    "result": "accepted"
   },
   "check": {
    "status": "in_progress",
    "segment": 1
   }
  }
 ],
 "segments": [
  {
   "index": 0,
   "start_step": 0,
   "prize_count": 0,
   "result": {
    "outcome": "sudden_death"
   }
  },
  {
   "index": 1,
   "start_step": 89,
   "prize_count": 1,
   "result": {
    "outcome": "win",
    "winner": 0
   }
  }
 ],
 "footer": {
  "reason": "game_over",
  "steps": 140,
  "final_state_digest": "<sha256>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "spectator": {
  "segment": {
   "index": 1,
   "prize_count": 1,
   "previous": [
    {
     "index": 0,
     "outcome": "sudden_death"
    }
   ]
  }
 }
}
```

#### EX8-REPLAY-REFUSED: 非対応の版・規約による再現の拒否（`api_status`: illustrative）

記録の規約集合 CS-KYUURA-PLAY-S2A@1 の照合値が、この実装の登録と違う（または記録の形式の版 2 をこの実装が知らない）

```json
{
 "replay": "unsupported",
 "reasons": [
  {
   "item": "convention_set.digest",
   "recorded": "<記録の照合値>",
   "expected": "<登録の照合値>"
  },
  {
   "item": "kyuura_replay_format",
   "recorded": 2,
   "supported": [
    1
   ]
  }
 ],
 "category": "compatibility",
 "diagnostic_id": "UNSUPPORTED_CONVENTION_SET"
}
```

#### EX9-HALTED: 操作の結果として停止した状態（`api_status`: illustrative）

番の終わりを受け付け、ポケモンチェックで未裁定の場面に当たって HALTED になる（拒否ではない）

```json
{
 "kyuura_diagnostic_schema": 1,
 "outcome": "accepted",
 "category": null,
 "diagnostic_id": null,
 "status": "halted",
 "halt": {
  "category": "unresolved_ruling",
  "diagnostic_id": "UNRESOLVED_SCRAM_TIMING",
  "case_id": null,
  "case_status": "not_identified",
  "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンは対戦を止めました。",
  "interrupted": false
 },
 "case_status": null,
 "stage": "turn_action",
 "continuable": false,
 "next": [],
 "ref": {
  "game_id": "g-0005",
  "segment": 0,
  "step": 77,
  "decision_id": null
 },
 "convention_set": {
  "id": "CS-KYUURA-CURRENT",
  "version": 1,
  "digest": "<照合値>"
 }
}
```

見る人ごとの写し（null は送らない）:

```json
{
 "actor": {
  "status": "halted",
  "halt": {
   "diagnostic_id": "UNRESOLVED_SCRAM_TIMING"
  }
 },
 "opponent": {
  "status": "halted",
  "halt": {
   "diagnostic_id": "UNRESOLVED_SCRAM_TIMING"
  }
 },
 "spectator": {
  "status": "halted",
  "halt": {
   "diagnostic_id": "UNRESOLVED_SCRAM_TIMING"
  }
 }
}
```
<!-- generated:examples end -->

## 10. 判断事項と実装計画

利用者の判断が要る事項（推奨つき）と、実装の単位・順・完了基準は [diagnostics-replay-api-implementation-plan.md](diagnostics-replay-api-implementation-plan.md) にあります。この仕様の作成の依頼は、ここに書いた提案のすべての承認ではありません。

## 11. 検証と未確認

- `python scripts/build_diagnostics_replay_api_design.py --check` は、JSON と文書の生成区画が同じ元から作ったものか、参照（ファイル・記号・停止コード・事例）が実在するか、分類・情報境界・記録・実装単位の矛盾（内部エラーをほかの分類にする規則、検証者だけの値が見る人に見える行、閲覧用記録の秘密の項目、コインの結果を入力にする項目、依存の循環など）がないかを確かめます。`tests/test_diagnostics_replay_api_design.py` は、わざと壊した仕様で、これらの確かめが問題を見つけることを確かめます
- 未確認:
  - 形式 35 が状態を落とさず表すか（U6 の最初の監査）
  - v0.135〜v0.151 の対象群の外の拒否の文が、配分によらないか
  - 技術的制限の上限が、どれも公開の情報だけで決まるか（v0.117 の約束は 1 枚の指定の回数について。上限ごとの確認は U1）
  - Python の版の違いで同じ乱数の列になるか（記録はするが、保証の範囲は D-RUNTIME）
- この作業では、エンジン・規約集合・カードデータ・固定デッキ・過去の参照データを変えていません（基点 `7e4a875` からの差は、この仕様の 5 つのファイルと、README・実装状況の参照の 1 行ずつ）。全体テスト・lockstep・大規模な対戦は実行していません
- この作業で実行した確かめ（終了コードは確かめの本体から）:
  - `build_diagnostics_replay_api_design.py --check`: problems=0（終了コード 0）。`tests.test_diagnostics_replay_api_design`: 19 テスト OK
  - 既存の生成物の `--check`（停止の方針の台帳・共通規約の設計案・同梱の規約集合の記録・実装上の仮定・正規化の再確認）: どれも終了コード 0（台帳・記録は変えていない）
  - 変えた文書（README・実装状況）を読むテストのメソッド 14 件: OK
  - ruff 0.17.2（基点と同じ版・設定）: 新しいスクリプトとテストに指摘なし。新しい抑制はない
  - `check_implementation_assumptions.py --sites`: 基点の木と比べて増えた候補は 1 件（`S-d3d1034633c7`。実装計画 6 章の完了基準「既存のテストの結果が変わらない」。実装上の仮定ではない）。文面は変えていない
  - 例の `NOT_YOUR_TURN` は `checks.require_turn` の拒否のコードであることをコードで確かめた（盤面の実行はしていない）。ほかの例のコード・事例が、エンジンのソース・台帳・場面の索引にあることは `--check` が確かめる
- 途中で見つけたこと: 否定のテストに停止コードの接頭辞（`UNRESOLVED_`）を持つ架空のコードを書くと、停止の方針の台帳の走査（`scripts/stop_policy_scan.py`。`tests/` も読む）がテストだけのコードとして数え、台帳の `--check` が差を出した。架空の値は接頭辞のない名前にした（台帳は変えていない）
