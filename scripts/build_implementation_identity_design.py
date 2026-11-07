"""実装の識別と互換性の判定の新しい方式の設計案 docs/implementation-identity-design.json を作る・確かめる（設計だけ。現行の識別・対応の判定は変えない）。

    python scripts/build_implementation_identity_design.py --write   # JSON と文書の生成区画（表）を、このスクリプトの SPEC から書き直す
    python scripts/build_implementation_identity_design.py --check   # JSON・生成区画が作り直したものと同じか、パッケージの全ファイルに分類があるか（replay_record.package_files と
                                                                     # 名前で照らす）、ゲームの挙動の部品が記録・検証の部品を読み込まないか、識別子の値がコードと同じか、
                                                                     # 機能ごとの判定がすべての部品を扱っているか

- 設計の唯一の元は、このスクリプトの ``SPEC``。JSON と文書の表はここから作る（二重に手で書かない）。生成区画の外（本文）は手で書く
- 表の書き出しと生成区画の置きかえは、状態スナップショットの仕様案の生成器（scripts/build_state_snapshot_design.py）の関数をそのまま使う
- 利用者が採用したのは原則（ADOPT-IDENTITY-PRINCIPLES）だけ。新しい方式の細部・移行は採用していない（``approval`` は ``not_approved``。判断事項はどれも ``pending``）
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "implementation-identity-design.json"
DESIGN = ROOT / "docs" / "implementation-identity-design.md"
PACKAGE = ROOT / "kyuura_engine"

_helpers_spec = importlib.util.spec_from_file_location("build_state_snapshot_design", ROOT / "scripts" / "build_state_snapshot_design.py")
_H = importlib.util.module_from_spec(_helpers_spec)
_helpers_spec.loader.exec_module(_H)
_cell, _table, render_into, dump = _H._cell, _H._table, _H.render_into, _H.dump

# ---------------------------------------------------------------- 分類

LAYERS = {
    "game_behavior": "ゲームの挙動（状態の遷移・効果・規則・カードデータ・エンジンが読む観測と書き出し）",
    "record_verification": "記録・検証の機能（診断・収集・再実行・閲覧用記録・スナップショット）",
    "api_format": "API の形式（パッケージの公開の入口と、各データ形式・方式の識別子）",
}

GAME_CODE = (
    "cards.py", "checks.py", "coins.py", "commands.py", "conditions.py", "continuous.py", "conventions.py", "damage.py", "decisions.py", "deck.py",
    "decks.py", "effects.py", "engine.py", "errors.py", "evolution.py", "faceup.py", "heights.py", "history.py", "interruption.py", "judge.py",
    "markers.py", "movement.py", "observation.py", "persistent.py", "procedures.py", "reactions.py", "rng.py", "rules.py", "serialize.py",
    "stadiums.py", "state.py", "sudden_death.py", "zones.py",
    "resolution/__init__.py", "resolution/catalog.py", "resolution/codec.py", "resolution/contract.py", "resolution/events.py", "resolution/flow.py",
    "resolution/kernel.py", "resolution/preflight.py", "resolution/programs.py", "resolution/questions.py", "resolution/unbounded.py",
    "resolution/v013_checks.py",
)
GAME_DATA = ("data/kyuura_cards.json", "data/card_verification.json", "data/species_heights.json", "data/convention_records.json")
PROVENANCE_DATA = ("data/card_sources.json", "data/research_links.json")

COMPONENTS = [
    {"id": "game_behavior", "layer": "game_behavior", "files": list(GAME_CODE + GAME_DATA + PROVENANCE_DATA),
     "role": "対戦の状態の遷移・受理と拒否・乱数の使い方・ログ・観測（engine.py・effects.py が observation.py を読み込み、observation.py が serialize.py を読み込むので、"
             "観測と状態の書き出しもここに入る）・カードデータ・固定デッキ・規約集合の登録の記録",
     "note": "data/card_sources.json・data/research_links.json は実行時にエンジンが読まない来歴のデータ（スクリプト・テストだけが読む）。分けるかは D-PROVENANCE。"
             "初版は保守的にゲームの挙動に入れる"},
    {"id": "diagnostics", "layer": "record_verification", "files": ["diagnostics.py", "data/diagnostic_catalog.json"],
     "role": "診断の型・コード表による分類・情報境界・状態の区分（status_of・next_actions）", "note": "記録の各行の分類（status・diagnostic）を決める"},
    {"id": "adapter", "layer": "record_verification", "files": ["adapter.py"], "role": "コマンドの実行結果（accepted・rejected・failed）と本人・相手・観戦者の知らせ",
     "note": "記録の各行の outcome を決める"},
    {"id": "replay_record", "layer": "record_verification", "files": ["replay_record.py"],
     "role": "完全な再現用記録の収集・形式・構造の検証・確認値（state_check・checks・接続用確認値の呼び出し）・現行の識別の計算", "note": "記録を書く側と読む側の両方"},
    {"id": "replay_run", "layer": "record_verification", "files": ["replay_run.py"], "role": "完全な記録の再実行と照合（U4）", "note": "読む側だけ（記録の値を作らない）"},
    {"id": "view_record", "layer": "record_verification", "files": ["view_record.py"], "role": "閲覧用記録の作成・構造の検証（U5）", "note": "閲覧用記録を書く側と読む側"},
    {"id": "snapshot", "layer": "record_verification", "files": ["snapshot.py"], "role": "状態スナップショットの保存・復元の符号化（コーデック）・接続用確認値（U6）",
     "note": "符号化の対応表は SNAPSHOT_FORMAT の中身で、名前のついた方式を持たない（初版は部品の識別の一致で守る）"},
    {"id": "snapshot_replay", "layer": "record_verification", "files": ["snapshot_replay.py"], "role": "完全な記録とスナップショットの接続（U6-S5）", "note": "読む側だけ"},
    {"id": "public_facade", "layer": "api_format", "files": ["__init__.py"],
     "role": "パッケージの公開の名前（import と __all__）と、エンジンの版の文字列（__version__）",
     "note": "処理を持たない（--check が import・代入・説明の文だけであることを確かめる）。版の文字列はここにあるので、今は版を上げるたびに behavior_digest が変わる（4 章）"},
    {"id": "legal_actions", "layer": "api_format", "files": ["legal_actions.py"],
     "role": "合法手 API（U7。docs/legal-actions-api-design.md）の操作候補・必要な入力の作成と、候補からの送信（U7-1 は決定への回答と番を終える。docs/legal-actions-u7-1.md）",
     "note": "v0.160 で加えた。U2 の HostedGame・CommandResult と observe を使う（別の実行器を持たない）。現行の方式では behavior_digest に入る"},
    {"id": "client_api", "layer": "api_format", "files": ["client_api.py"],
     "role": "クライアント向けの最小のアダプタ（JSON にできる要求・応答と、閲覧者ごとの公開の更新。docs/client-api-v0.164.md）",
     "note": "v0.164 で加えた。U7 の入口（legal_actions）と observe・診断を使い、別の実行器を持たない。保存した値を読まない（記録・スナップショットの互換の判定に関わらない）。現行の方式では behavior_digest に入る"},
]

# 現行の方式（変えない）。--check がコードの値と照らす
CURRENT = {
    "method": "kyuura-package-files-sha256/1",
    "instrumentation_files": ["adapter.py", "diagnostics.py", "replay_record.py", "data/diagnostic_catalog.json"],
    "definition": "パッケージの .py（__pycache__ を除く）と data/*.json を、改行を LF・BOM を除いた中身の sha256 で連ねた sha256。INSTRUMENTATION_FILES の 4 つが "
                  "instrumentation_digest、残りがすべて behavior_digest",
    "limits": [
        ("あとで加えた記録・検証のモジュール（replay_run.py・view_record.py・snapshot.py・snapshot_replay.py）は INSTRUMENTATION_FILES にないので behavior_digest に入る。"
         "これらを直すと、ゲームの処理が同じでも、それまでの記録・スナップショットは unsupported になる（v0.159 の総合検証 2.1 節 A）"),
        "__init__.py（__version__）が behavior_digest に入るので、版を上げるだけで behavior_digest が変わる",
        ("U4・S5（replay_record.support_problems）は behavior_digest と版だけを比べ、instrumentation_digest を比べない。スナップショット（snapshot._check_support）は "
         "instrumentation_digest も比べる（DS-INSTRUMENTATION）。今は版の一致の条件がこの差を覆っている"),
        "部品ごとの識別がないので、ある機能が使わない部品の違いでも、その機能を拒む",
    ],
}

# 識別子の一覧。code は (モジュール, 名前)。--check がコードの値と同じことを確かめる
IDENTIFIERS = [
    {"id": "engine_version", "kind": "release", "code": ("kyuura_engine", "__version__"), "value": None,
     "meaning": "エンジンの版（リリースの名前）", "used_by": ["replay_record.support_problems（engine_version_differs）", "snapshot._check_support（同）",
                                                        "view_record の見出し（engine_version。読む側は比べない）", "serialize.state_to_dict の engine_version（確認値から除く）"]},
    {"id": "identity_method", "kind": "identity", "code": ("kyuura_engine.replay_record", "IDENTITY_METHOD"), "value": "kyuura-package-files-sha256/1",
     "meaning": "現行の実装の識別の方式", "used_by": ["replay_record.support_problems", "snapshot._check_support"]},
    {"id": "behavior_digest", "kind": "identity", "code": None, "value": None, "meaning": "現行の方式のゲームの挙動の側の識別（4 つの部品以外のすべて）",
     "used_by": ["replay_record.support_problems（implementation_differs）", "snapshot._check_support（同）"]},
    {"id": "instrumentation_digest", "kind": "identity", "code": None, "value": None, "meaning": "現行の方式の記録と診断の部品 4 つの識別",
     "used_by": ["snapshot._check_support（instrumentation_differs）。U4・S5 は比べない"]},
    {"id": "replay_format", "kind": "format", "code": ("kyuura_engine.replay_record", "REPLAY_FORMAT"), "value": 1, "meaning": "完全な再現用記録の形式（kyuura_replay_format）",
     "used_by": ["replay_record._structure（SUPPORTED_REPLAY_FORMATS）"]},
    {"id": "view_format", "kind": "format", "code": ("kyuura_engine.view_record", "VIEW_FORMAT"), "value": 1, "meaning": "閲覧用記録の形式（kyuura_view_format）",
     "used_by": ["view_record.validate_view_record"]},
    {"id": "snapshot_format", "kind": "format", "code": ("kyuura_engine.snapshot", "SNAPSHOT_FORMAT"), "value": 1, "meaning": "状態スナップショットの形式（kyuura_snapshot_format）",
     "used_by": ["snapshot の復元の段 2"]},
    {"id": "state_export_format", "kind": "format", "code": ("kyuura_engine.replay_record", "STATE_EXPORT_FORMAT"), "value": 35, "meaning": "確認値に使う状態の書き出しの形式",
     "used_by": ["replay_record.support_problems（state_export_format_unsupported）", "snapshot._formats"]},
    {"id": "state_check_method", "kind": "method", "code": ("kyuura_engine.replay_record", "STATE_CHECK_METHOD"), "value": "state-export-35-sha256/1",
     "meaning": "状態の確認値の方式", "used_by": ["replay_record.support_problems（check_method_unknown）", "snapshot._formats"]},
    {"id": "rng_check_method", "kind": "method", "code": ("kyuura_engine.replay_record", "RNG_CHECK_METHOD"), "value": "python-random-getstate-sha256/1",
     "meaning": "乱数の確認値の方式", "used_by": ["同上"]},
    {"id": "connection_check_method", "kind": "method", "code": ("kyuura_engine.replay_record", "CONNECTION_CHECK_METHOD"), "value": "kyuura-snapshot-state-sha256/1",
     "meaning": "接続用確認値の方式（任意の拡張）", "used_by": ["replay_record._check_extensions", "snapshot_replay（from_connection）"]},
    {"id": "record_identity_method", "kind": "method", "code": ("kyuura_engine.snapshot_replay", "RECORD_IDENTITY_METHOD"), "value": "kyuura-replay-header-sha256/1",
     "meaning": "記録の見分け（見出しの sha256。認証ではない）", "used_by": ["snapshot_replay.RecordPosition.record"]},
    {"id": "diagnostic_schema", "kind": "format", "code": ("kyuura_engine.diagnostics", "DIAGNOSTIC_SCHEMA"), "value": 1, "meaning": "診断の形式",
     "used_by": ["replay_record.support_problems（diagnostic_schema_unsupported）", "snapshot._formats", "view_record の見出し"]},
    {"id": "rng_format", "kind": "format", "code": ("kyuura_engine.rng", "RNG_FORMAT"), "value": "python-random-mt19937-v3", "meaning": "乱数の方式",
     "used_by": ["replay_record.runtime_identity（rng_scheme_differs）", "snapshot._formats"]},
    {"id": "runtime", "kind": "environment", "code": None, "value": None, "meaning": "Python の実装と版（major・minor）と乱数の方式",
     "used_by": ["replay_record.support_problems（runtime_differs）", "snapshot._check_support（同）"]},
    {"id": "dependencies", "kind": "dependency", "code": None, "value": None, "meaning": "ルールの組・カードデータ（リポジトリ・コミット・パス）・効果の登録表",
     "used_by": ["replay_record.support_problems（rules_unknown・card_data_differs・effects_differs）", "snapshot._check_support（同と card_pool_not_default）"]},
    {"id": "convention_set", "kind": "convention", "code": None, "value": None, "meaning": "規約集合の ID・版・照合値（固定した照合値と登録の内容）",
     "used_by": ["replay_record.support_problems（convention_set_unsupported）", "snapshot._check_support（同）", "conventions.require_state_conventions"]},
    {"id": "git_commit", "kind": "auxiliary", "code": None, "value": None, "meaning": "Git の HEAD（補助の情報。識別に使わない）", "used_by": ["記録・スナップショットの見出し（任意）"]},
]

# 機能ごとの判定（新しい方式の推奨案）。required は一致が要る部品、reader は読む側（今の実装）で一致を求めない部品、unused は使わない部品
FEATURES = [
    {"id": "U4", "name": "U4 の全体の再現（replay）",
     "required": ["game_behavior", "diagnostics", "adapter", "replay_record"], "reader": ["replay_run"], "unused": ["view_record", "snapshot", "snapshot_replay", "public_facade", "legal_actions", "client_api"],
     "formats": ["replay_format", "state_export_format", "state_check_method", "rng_check_method", "diagnostic_schema", "rng_format", "runtime", "dependencies", "convention_set"],
     "auxiliary": ["engine_version", "git_commit", "game_id", "operation_id"],
     "note": "記録の各行の値（受理・拒否・コード・status・確認値）を作った部品は一致を求める。replay_record は書く側を兼ねるので、初版は一致を求める（緩めるかは D-WRITER）"},
    {"id": "SNAPSHOT", "name": "スナップショットの復元（restore_snapshot）",
     "required": ["game_behavior", "diagnostics", "snapshot"], "reader": [], "unused": ["adapter", "replay_record", "replay_run", "view_record", "snapshot_replay", "public_facade", "legal_actions", "client_api"],
     "formats": ["snapshot_format", "state_export_format", "state_check_method", "rng_check_method", "diagnostic_schema", "rng_format", "runtime", "dependencies", "convention_set"],
     "auxiliary": ["engine_version", "git_commit", "origin", "label"],
     "note": "符号化の対応表に名前のついた方式がないので、snapshot の部品の一致で守る（D-CODEC）。確認値の status は診断が決めるので diagnostics も一致を求める"},
    {"id": "S5", "name": "S5 の接続の再現（replay_from_snapshot）",
     "required": ["game_behavior", "diagnostics", "adapter", "replay_record", "snapshot"], "reader": ["replay_run", "snapshot_replay"],
     "unused": ["view_record", "public_facade", "legal_actions", "client_api"],
     "formats": ["replay_format", "snapshot_format", "state_export_format", "state_check_method", "rng_check_method", "connection_check_method", "record_identity_method",
                 "diagnostic_schema", "rng_format", "runtime", "dependencies", "convention_set"],
     "auxiliary": ["engine_version", "git_commit", "origin", "label"],
     "note": "記録の条件（U4）とスナップショットの条件の和。記録とスナップショットの部品の識別も互いに同じこと。from_connection は whole_record とは別の保証のまま"},
    {"id": "VIEW_FROM_REPLAY", "name": "完全な記録からの閲覧用記録の作成（view_records_from_replay）",
     "required": ["game_behavior", "diagnostics", "adapter", "replay_record"], "reader": ["replay_run", "view_record"],
     "unused": ["snapshot", "snapshot_replay", "public_facade", "legal_actions", "client_api"],
     "formats": ["replay_format", "state_export_format", "state_check_method", "rng_check_method", "diagnostic_schema", "rng_format", "runtime", "dependencies", "convention_set"],
     "auxiliary": ["engine_version", "git_commit"],
     "note": "U4 が succeeded のときだけ作る。作った閲覧用記録は今の view_record の形式で、見出しに作った側の部品の識別を書く（観測は game_behavior に入るので、観測の違いは U4 の条件で拒む）"},
    {"id": "VIEW_READ", "name": "閲覧用記録の読み取り（validate_view_record・表示）",
     "required": [], "reader": ["view_record"], "unused": ["game_behavior", "diagnostics", "adapter", "replay_record", "replay_run", "snapshot", "snapshot_replay", "public_facade", "legal_actions", "client_api"],
     "formats": ["view_format", "diagnostic_schema"],
     "auxiliary": ["engine_version", "convention_set"],
     "note": "表示用の記録で、再現の確かめではない（replay_verified はいつも偽）。形式の版と構造で読む。実装の識別の一致は求めない（今と同じ）。作った側の部品の識別は表示の補助"},
    {"id": "U7", "name": "将来の合法手 API（操作候補・必要な入力）",
     "required": ["game_behavior", "diagnostics", "adapter", "legal_actions"], "reader": [], "unused": ["replay_record", "replay_run", "view_record", "snapshot", "snapshot_replay", "public_facade", "client_api"],
     "formats": ["convention_set"],
     "auxiliary": ["engine_version"],
     "note": "処理可能性の区分に診断のコード表を使い、送信は U2 のアダプタ（HostedGame・CommandResult）を通す。候補はホストの中で、その時点の状態と動いている実装から作り、保存して別の実装で使わない（docs/legal-actions-api-design.md の状態との対応）。"
             "候補の応答の形式の版は U7 で新しく設ける（legal_actions_format）。保存した候補を別の実装で読むことは対応しない"},
]

VERSION_ANALYSIS = [
    {"case": "今（現行の方式）", "version_rule": "版が違えば U4・S5・スナップショットは unsupported", "effect": "版は毎回上がり、__init__.py の版の文字列が behavior_digest にも入るので、"
     "どのリリースのあとも前の記録は unsupported。版の一致の条件は behavior_digest の一致と重なり、独立の情報を足していない"},
    {"case": "部品を分けても、版の不一致で拒む", "version_rule": "部品の識別が同じでも、版が違えば unsupported", "effect": "改善しない。閲覧用記録だけを直したリリースでも版が上がるので、"
     "U4 の記録はやはり unsupported になる。分けた識別は、版が同じ開発中の木どうしでしか効かない"},
    {"case": "推奨: 版を補助の情報にする", "version_rule": "互換は機能ごとの部品の識別・形式と方式の識別子・依存・環境・規約集合で決め、版は表示と記録の補助",
     "effect": "記録・検証の部品だけを直したリリースのあとも、ゲームの挙動の部品とその機能が使う部品が同じなら U4 の記録を扱える。版の文字列は __init__.py から外し、"
               "どの識別にも入れない（移行の M2）"},
]

# ゲームの挙動のファイルがほかの層を読み込む既知の例外（--check が、ほかにないこと・使われなくなっていないことを確かめる）
DEPENDENCY_EXCEPTIONS = [
    {"file": "serialize.py", "imports": "__init__.py", "reason": "state_to_dict が engine_version（__version__）を書き出す（確認値からは除く）。版の文字列を読むだけ",
     "resolved_by": "M2（版の文字列を版だけのファイルへ移す）"},
]

PRINCIPLES = [
    {"id": "P-OLD-KEPT", "text": "現行の方式（kyuura-package-files-sha256/1）とその判定はそのまま残す。方式の名前の意味を変えない"},
    {"id": "P-NO-REINTERPRET", "text": "新しい方式から現行の方式へ、現行の方式から新しい方式へ、自動で読み替えない。現行の方式の記録は現行の判定だけで扱う"},
    {"id": "P-NO-SPLIT-COMPAT", "text": "分けたことだけを理由に、過去の記録を互換として扱わない（現行の方式の記録は部品の識別を持たないので、新しい判定に入れない）"},
    {"id": "P-METHODS", "text": "ゲームの挙動が同じでも、確認値の方式・復元の符号化・診断の分類・記録の形式の違いを無視しない（機能ごとに一致を求める部品・識別子を表にする）"},
    {"id": "P-UNKNOWN-REJECT", "text": "分類のない部品・知らない方式・知らない形式の版・知らない部品の識別は、安全側に拒否する（unsupported）"},
    {"id": "P-NOT-AUTH", "text": "識別のハッシュは、偶然の違いを見つける値で、署名・出所の認証ではない（記録を書いた人が値を書きかえられる）"},
    {"id": "P-NOT-DECLARATION", "text": "互換を認める根拠を、版の番号の大小や「ゲームの処理を変えていない」という申告にしない。ファイルの中身の識別と、固定した入力に対する方式の出力（既知の答え）で決める"},
]

NEW_METHOD = {
    "name": "kyuura-component-identity/1",
    "status": "proposed",
    "definition": "部品（COMPONENTS）ごとに、その部品のファイルを現行と同じ正規化（改行を LF・BOM を除く）で連ねた sha256。部品の一覧と部品ごとのファイルの一覧はこの設計の分類で決め、"
                  "分類のないファイルがあれば識別を作らない（収集・保存を拒む）",
    "record_fields": ["identity.method", "identity.components（部品 → {digest, files}）", "identity.classification_digest（部品とファイルの対応の sha256）", "version（補助）"],
    "guards": [
        "分類の漏れ: パッケージのファイルの一覧と分類を名前で照らす（この設計の --check と同じ）。新しいファイルを加えたら、分類を書くまで --check が失敗する",
        "依存の向き: ゲームの挙動の部品のファイルは、ほかの層の部品を読み込まない（AST の import で確かめる）。読み込めば、その部品はゲームの挙動に入る",
        "公開の入口: public_facade のファイルは import・代入・説明の文だけ（処理を持たない）",
        "方式の既知の答え: 確認値・接続用確認値・記録の見分けの方式ごとに、固定した状態・見出しに対する値をテストに固定する。出力が変われば方式の名前を変える（同じ名前で意味を変えない）",
        "符号化の既知の答え: スナップショットの符号化に、固定した状態の保存の JSON をテストに固定する（D-CODEC で方式の名前をつけるまで、snapshot の部品の一致も求める）",
    ],
}

MIGRATION = [
    {"step": 1, "id": "M0", "what": "この設計（文書と --check）。現行の識別・判定・形式は変えない", "changes_current": False, "status": "this_change"},
    {"step": 2, "id": "M1", "what": "方式の既知の答えのテスト（確認値・接続用確認値・記録の見分け・スナップショットの符号化）を加える。識別・判定は変えない", "changes_current": False, "status": "planned"},
    {"step": 3, "id": "M2", "what": "版の文字列を __init__.py から別のファイル（版だけを持つ。public_facade の外の release の扱い）へ移す。現行の方式の定義（全ファイル − 4 つ）は変えないので、"
     "現行の behavior_digest の値はこのリリースで変わる（いつもと同じ）", "changes_current": False, "status": "planned"},
    {"step": 4, "id": "M3", "what": "新しい方式の識別の計算（部品ごとの digest）を加える。書く側は使わない（計算とその --check だけ）", "changes_current": False, "status": "planned"},
    {"step": 5, "id": "M4", "what": "新しい形式の版（kyuura_replay_format 2・kyuura_snapshot_format 2）で、見出しに新しい方式の識別を書く。形式 1 の書き出し・読み取り・判定は残す",
     "changes_current": False, "status": "planned"},
    {"step": 6, "id": "M5", "what": "形式 2 の読み取りの判定を FEATURES の表どおりに実装する（機能ごとに一致を求める部品・形式・方式。版は補助）。形式 1 は現行の判定のまま",
     "changes_current": False, "status": "planned"},
    {"step": 7, "id": "M6", "what": "回帰テスト: 形式 1 の記録の扱いが変わらない／形式 2 で view_record だけを変えた木でも U4 の記録を扱える／game_behavior の 1 ファイルを変えると unsupported／"
     "分類のないファイルで識別を作らない／方式の既知の答えが変われば失敗する", "changes_current": False, "status": "planned"},
    {"step": 8, "id": "M7", "what": "書き出しの既定を形式 2 にするか（D-DEFAULT）。形式 1 の書き出しを残す期間", "changes_current": False, "status": "planned"},
]

DECISIONS = [
    {"id": "D-PROVENANCE", "question": "実行時にエンジンが読まない来歴のデータ（card_sources.json・research_links.json）をゲームの挙動から外すか", "recommendation":
     "初版は外さない（保守的）。外すなら、実行時に読まないことを確かめるテスト（読み込みの経路の検査）を先に作る", "status": "pending"},
    {"id": "D-WRITER", "question": "U4 で replay_record（書く側と読む側を兼ねる）の一致を求め続けるか", "recommendation":
     "初版は求める。書く側と読む側を分けるか、形式 2 の書き出しの既知の答えのテストができたら緩める", "status": "pending"},
    {"id": "D-CODEC", "question": "スナップショットの符号化に名前のついた方式をつけるか", "recommendation": "つける（kyuura-snapshot-codec/1 など）。それまでは snapshot の部品の一致を求める",
     "status": "pending"},
    {"id": "D-VERSION-AUX", "question": "新しい方式で、エンジンの版を互換の条件から外し、補助の情報にするか", "recommendation": "外す（4 章。外さなければ分けても改善しない）",
     "status": "pending"},
    {"id": "D-FORMAT-BUMP", "question": "新しい識別を書くのに、形式の版を上げるか（形式 1 の任意の拡張にしないか）", "recommendation":
     "上げる（判定の規則が変わるので、形式 1 の読む側が新しい記録を形式 1 の規則で読まないように）", "status": "pending"},
    {"id": "D-DEFAULT", "question": "書き出しの既定を形式 2 にする時期と、形式 1 を書ける期間", "recommendation": "M6 の回帰テストのあと。形式 1 の読み取りはやめない", "status": "pending"},
    {"id": "D-RUNTIME-PATCH", "question": "Python の版の比べを major・minor のままにするか", "recommendation": "今のまま（ADOPT-U3 の D-RUNTIME）。変えない", "status": "pending"},
]

ADOPTION = {
    "id": "ADOPT-IDENTITY-PRINCIPLES", "date": "2026-11-07", "by": "利用者",
    "scope": "実装の識別を、ゲームの挙動・記録と検証の機能・API の形式の 3 つの責任に分けることを、新しい識別の方式として設計すること（既存の方式の意味を変えない。分けたことだけを理由に"
             "過去の記録を互換として扱わない）。新しい方式の細部・移行・判定の変更は採用していない",
}

SPEC = {
    "id": "IMPLEMENTATION-IDENTITY-DESIGN", "status": "proposed", "approval": "not_approved",
    "adoption": ADOPTION, "layers": LAYERS, "components": COMPONENTS, "current": CURRENT, "identifiers": IDENTIFIERS, "features": FEATURES,
    "dependency_exceptions": DEPENDENCY_EXCEPTIONS, "version_analysis": VERSION_ANALYSIS, "principles": PRINCIPLES, "new_method": NEW_METHOD, "migration": MIGRATION, "decisions": DECISIONS,
}


def build() -> dict:
    data = json.loads(json.dumps(SPEC, ensure_ascii=False))
    for item in data["identifiers"]:
        if item["code"] is not None:
            item["code"] = ".".join(item["code"])
    return data


# ---------------------------------------------------------------- 表


def _file_rows(spec: dict) -> list[list]:
    rows = []
    for c in spec["components"]:
        for name in c["files"]:
            rows.append([f"`{name}`", c["id"], c["layer"]])
    return sorted(rows)


def blocks(spec: dict) -> dict[str, list[str]]:
    comps = spec["components"]
    out = {
        "adoption": [f"- `{spec['adoption']['id']}`（{spec['adoption']['date']}・{spec['adoption']['by']}）: {spec['adoption']['scope']}",
                     f"- 設計案の状態: `{spec['status']}`・承認 `{spec['approval']}`"],
        "layers": _table(["層", "責任"], [[f"`{k}`", v] for k, v in spec["layers"].items()]),
        "components": _table(["部品", "層", "ファイルの数", "役割", "注"],
                             [[f"`{c['id']}`" + ("（予定）" if c.get("status") == "planned" else ""), c["layer"], len(c["files"]), c["role"], c["note"]] for c in comps]),
        "files": _table(["ファイル", "部品", "層"], _file_rows(spec)),
        "current": [f"- 方式: `{spec['current']['method']}`", f"- 定義: {spec['current']['definition']}",
                    "- INSTRUMENTATION_FILES: " + "・".join(f"`{n}`" for n in spec["current"]["instrumentation_files"]), "- 制限:"]
                   + [f"  - {t}" for t in spec["current"]["limits"]],
        "identifiers": _table(["識別子", "種類", "コード", "値", "意味", "使う場所"],
                              [[f"`{i['id']}`", i["kind"], f"`{i['code']}`" if i["code"] else "", "" if i["value"] is None else f"`{i['value']}`", i["meaning"], i["used_by"]]
                               for i in spec["identifiers"]]),
        "features": _table(["機能", "一致が要る部品", "読む側（一致を求めない）", "使わない部品", "形式・方式・環境の対応", "補助の情報", "注"],
                           [[f["name"], [f"`{x}`" for x in f["required"]] or "なし", [f"`{x}`" for x in f["reader"]] or "なし", [f"`{x}`" for x in f["unused"]],
                             [f"`{x}`" for x in f["formats"]], f["auxiliary"], f["note"]] for f in spec["features"]]),
        "dependency": _table(["ファイル", "読み込む", "理由", "解消"], [[f"`{e['file']}`", f"`{e['imports']}`", e["reason"], e["resolved_by"]]
                                                                     for e in spec["dependency_exceptions"]]),
        "version": _table(["場合", "版の規則", "結果"], [[v["case"], v["version_rule"], v["effect"]] for v in spec["version_analysis"]]),
        "principles": [f"- `{p['id']}`: {p['text']}" for p in spec["principles"]],
        "new-method": [f"- 名前: `{spec['new_method']['name']}`（{spec['new_method']['status']}）", f"- 定義: {spec['new_method']['definition']}",
                       "- 記録に書く項目: " + "・".join(spec["new_method"]["record_fields"]), "- 守り:"] + [f"  - {g}" for g in spec["new_method"]["guards"]],
        "migration": _table(["段", "ID", "内容", "現行の判定を変えるか", "状態"],
                            [[m["step"], m["id"], m["what"], m["changes_current"], m["status"]] for m in spec["migration"]]),
        "decisions": _table(["ID", "問い", "推奨", "状態"], [[f"`{d['id']}`", d["question"], d["recommendation"], d["status"]] for d in spec["decisions"]]),
    }
    return out


DESIGN_BLOCKS = ("adoption", "layers", "components", "files", "dependency", "current", "identifiers", "features", "version", "principles", "new-method", "migration", "decisions")

# ---------------------------------------------------------------- 確かめ


def package_files() -> list[str]:
    from kyuura_engine.replay_record import package_files as current

    return current()


def coverage_problems(spec: dict, files: list[str] | None = None) -> list[str]:
    files = package_files() if files is None else files
    owner: dict[str, list[str]] = {}
    for c in spec["components"]:
        for name in c["files"]:
            owner.setdefault(name, []).append(c["id"])
    problems = [f"{name} が 2 つ以上の部品にある（{ids}）" for name, ids in sorted(owner.items()) if len(ids) > 1]
    problems += [f"{name} に分類がない（パッケージに加わったファイル）" for name in files if name not in owner]
    problems += [f"{name} の分類があるが、パッケージにない" for name in sorted(owner) if name not in files]
    return problems


def _imports(path: pathlib.Path, name: str) -> set[str]:
    """パッケージの中のファイル ``name``（例 resolution/flow.py）が読み込むパッケージの中のモジュールのファイル名。"""
    package = name[:-3].split("/")[:-1]  # ファイルのあるパッケージ（[] はパッケージの根）
    found: set[str] = set()

    def module_file(mod: list[str]) -> str | None:
        for candidate in ("/".join(mod + ["__init__"]) + ".py", "/".join(mod) + ".py"):
            if (PACKAGE / candidate).exists():
                return candidate
        return None

    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - (node.level - 1)]
                mod = base + (node.module.split(".") if node.module else [])
            elif node.module == "kyuura_engine" or (node.module or "").startswith("kyuura_engine."):
                mod = node.module.split(".")[1:]
            else:
                continue
            subs = [module_file(mod + [alias.name]) for alias in node.names]  # from . import codec（モジュールそのものを読み込む）
            found.update(s for s in subs if s)
            if module_file(mod) and (not module_file(mod).endswith("__init__.py") or not all(subs)):
                found.add(module_file(mod))  # パッケージの __init__ は、そこから名前を読むときだけ（from . import __version__）
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("kyuura_engine.") and module_file(alias.name.split(".")[1:]):
                    found.add(module_file(alias.name.split(".")[1:]))
    found.discard(name)
    return found


_IMPORTS_CACHE: dict[str, tuple[float, frozenset[str]]] = {}


def code_imports() -> dict[str, set[str]]:
    """ファイルごとの読み込み（AST を読むのは時間がかかるので、更新時刻が同じ間は前の結果を使う。返す値は呼ぶ側が変えてよい写し）。"""
    result = {}
    for name in package_files():
        if not name.endswith(".py"):
            continue
        mtime = (PACKAGE / name).stat().st_mtime
        cached = _IMPORTS_CACHE.get(name)
        if cached is None or cached[0] != mtime:
            cached = (mtime, frozenset(_imports(PACKAGE / name, name)))
            _IMPORTS_CACHE[name] = cached
        result[name] = set(cached[1])
    return result


def dependency_problems(spec: dict, imports: dict[str, set[str]] | None = None) -> list[str]:
    """ゲームの挙動のファイルがほかの層のファイルを読み込まないか。既知の例外（``dependency_exceptions``）は、理由と解消の段を書いたものだけ。使われなくなった例外も問題にする。"""
    imports = code_imports() if imports is None else imports
    component = {name: c["id"] for c in spec["components"] for name in c["files"]}
    game = {c["id"] for c in spec["components"] if c["layer"] == "game_behavior"}
    allowed = {(e["file"], e["imports"]) for e in spec["dependency_exceptions"]}
    problems, used = [], set()
    for name, targets in sorted(imports.items()):
        if component.get(name) not in game:
            continue
        for target in sorted(targets):
            if component.get(target) in game:
                continue
            if (name, target) in allowed:
                used.add((name, target))
                continue
            problems.append(f"ゲームの挙動のファイル {name} が、ほかの層の {target}（{component.get(target)}）を読み込む")
    problems += [f"依存の例外 {a} → {b} は、もう使われていない（例外から消す）" for a, b in sorted(allowed - used)]
    return problems


def facade_problems(spec: dict, sources: dict[str, str] | None = None) -> list[str]:
    problems = []
    for c in spec["components"]:
        if c["id"] != "public_facade":
            continue
        for name in c["files"]:
            text = sources[name] if sources is not None else (PACKAGE / name).read_text(encoding="utf-8")
            for node in ast.parse(text).body:
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
                    continue
                problems.append(f"公開の入口 {name} に処理（{type(node).__name__}・{node.lineno} 行）がある")
    return problems


def identifier_problems(spec: dict, values: dict[str, object] | None = None) -> list[str]:
    problems = []
    for item in spec["identifiers"]:
        if item["code"] is None:
            continue
        module, name = item["code"].rsplit(".", 1)
        if values is not None and item["id"] in values:
            actual = values[item["id"]]
        else:
            actual = getattr(importlib.import_module(module), name)
        if item["value"] is not None and actual != item["value"]:
            problems.append(f"識別子 {item['id']} の値 {item['value']!r} が、コード（{item['code']}）の {actual!r} と違う")
    from kyuura_engine import replay_record as R

    if list(R.INSTRUMENTATION_FILES) != spec["current"]["instrumentation_files"]:
        problems.append("現行の INSTRUMENTATION_FILES が、設計に写した一覧と違う")
    if R.IDENTITY_METHOD != spec["current"]["method"]:
        problems.append("現行の識別の方式の名前が、設計に写したものと違う")
    return problems


def spec_problems(spec: dict) -> list[str]:
    problems = []
    if spec.get("approval") != "not_approved" or spec.get("status") != "proposed":
        problems.append("設計案が承認済みになっている（原則の採用は adoption に書く）")
    layers = set(spec["layers"])
    comp_ids = [c["id"] for c in spec["components"]]
    if len(set(comp_ids)) != len(comp_ids):
        problems.append("部品の ID が重なる")
    for c in spec["components"]:
        if c["layer"] not in layers:
            problems.append(f"部品 {c['id']} の層 {c['layer']} が語彙にない")
        if not c["files"] and c.get("status") != "planned":
            problems.append(f"部品 {c['id']} にファイルがない（予定の部品なら status を planned に）")
    ident_ids = {i["id"] for i in spec["identifiers"]}
    aux_ok = ident_ids | {"game_id", "operation_id", "origin", "label"}
    for f in spec["features"]:
        mentioned = f["required"] + f["reader"] + f["unused"]
        for cid in mentioned:
            if cid not in comp_ids:
                problems.append(f"機能 {f['id']} の部品 {cid} が部品の一覧にない")
        missing = [cid for cid in comp_ids if cid not in mentioned]
        if missing:
            problems.append(f"機能 {f['id']} が部品 {missing} を扱っていない（不明は拒否の原則。一致・読む側・使わないのどれかに分ける）")
        if len(mentioned) != len(set(mentioned)):
            problems.append(f"機能 {f['id']} で同じ部品が 2 つの扱いにある")
        for x in f["formats"]:
            if x not in ident_ids:
                problems.append(f"機能 {f['id']} の形式・方式 {x} が識別子の一覧にない")
        for x in f["auxiliary"]:
            if x not in aux_ok:
                problems.append(f"機能 {f['id']} の補助の情報 {x} が識別子の一覧にない")
        if "engine_version" in f["formats"]:
            problems.append(f"機能 {f['id']} がエンジンの版を互換の条件にしている（新しい方式では補助の情報。4 章）")
    feats = {f["id"]: f for f in spec["features"]}
    for key in ("U4", "SNAPSHOT", "S5", "VIEW_FROM_REPLAY", "VIEW_READ", "U7"):
        if key not in feats:
            problems.append(f"機能 {key} の行がない")
    if "game_behavior" not in feats.get("U4", {}).get("required", []):
        problems.append("U4 がゲームの挙動の一致を求めていない")
    if set(feats.get("S5", {}).get("required", [])) < set(feats.get("U4", {}).get("required", [])) | set(feats.get("SNAPSHOT", {}).get("required", [])):
        problems.append("S5 が U4 とスナップショットの条件の和を求めていない")
    if feats.get("VIEW_READ", {}).get("required"):
        problems.append("閲覧用記録の読み取りが実装の一致を求めている（表示用の記録。今と同じく形式で読む）")
    steps = [m["step"] for m in spec["migration"]]
    if steps != list(range(1, len(steps) + 1)):
        problems.append("移行の段の番号が連続していない")
    if any(m["changes_current"] for m in spec["migration"]):
        problems.append("移行の段が現行の判定を変える（現行の方式は残す）")
    pids = {p["id"] for p in spec["principles"]}
    for need in ("P-OLD-KEPT", "P-NO-REINTERPRET", "P-NO-SPLIT-COMPAT", "P-METHODS", "P-UNKNOWN-REJECT", "P-NOT-AUTH", "P-NOT-DECLARATION"):
        if need not in pids:
            problems.append(f"原則 {need} がない")
    if spec["new_method"]["name"] == spec["current"]["method"]:
        problems.append("新しい方式が現行の方式と同じ名前（意味を変えずに名前を分ける）")
    for d in spec["decisions"]:
        if d.get("status") != "pending":
            problems.append(f"判断事項 {d['id']} の状態が pending でない（採用の記録がない）")
    return problems + coverage_problems(spec) + dependency_problems(spec) + facade_problems(spec) + identifier_problems(spec)


def check(written: dict, design: str) -> list[str]:
    spec = build()
    problems = []
    if written != spec:
        problems.append("書いた JSON が、作り直した設計案と違う（--write で作り直す）")
    new, block_problems = render_into(design, blocks(spec), DESIGN_BLOCKS)
    problems += [f"設計の文書: {p}" for p in block_problems]
    if new != design:
        problems.append("設計の文書の生成区画が、作り直したものと違う（--write で作り直す）")
    return problems + spec_problems(written)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    spec = build()
    if args.write:
        problems = spec_problems(spec)
        if problems:
            print("\n".join(problems))
            return 1
        OUTPUT.write_text(dump(spec), encoding="utf-8", newline="\n")
        text, block_problems = render_into(DESIGN.read_text(encoding="utf-8"), blocks(spec), DESIGN_BLOCKS)
        if block_problems:
            print("\n".join(f"{DESIGN.name}: {p}" for p in block_problems))
            return 1
        DESIGN.write_text(text, encoding="utf-8", newline="\n")
        print("書いた")
        return 0
    if not OUTPUT.exists():
        print("設計案の JSON がない（--write で作る）")
        return 1
    problems = check(json.loads(OUTPUT.read_text(encoding="utf-8")), DESIGN.read_text(encoding="utf-8"))
    print("\n".join(problems) if problems else "problems=0")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
