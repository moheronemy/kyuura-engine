"""診断 API と対戦記録・再現インターフェースの仕様案 docs/diagnostics-replay-api-design.json を作る・確かめる（仕様だけ。エンジンの動作は変えない）。

    python scripts/build_diagnostics_replay_api_design.py --write   # JSON と、2 つの文書の生成区画（表・例）を、このスクリプトの SPEC から書き直す
    python scripts/build_diagnostics_replay_api_design.py --check   # JSON・生成区画が作り直したものと同じか、参照（ファイル・記号・停止コード・事例）に欠けがないか、
                                                                    # 情報境界・分類・記録・実装単位の矛盾がないか

- 仕様の唯一の元は、このスクリプトの ``SPEC``。JSON と文書の表・例はここから作る（二重に手で書かない）。文書の生成区画の外（本文の説明）は手で書く。
- 文書の生成区画は ``<!-- generated:名前 begin -->`` と ``<!-- generated:名前 end -->`` の間。--write は区画の中だけを置きかえる。
- 停止コード・事例は停止の方針の台帳（docs/stop-policy-classification.json）と同梱の場面の索引（kyuura_engine/data/convention_records.json）から引くだけで、書き換えない。
- 例（``examples``）は未実装の API の形の例示。実在の API の出力ではない（``api_status`` が ``not_implemented``）。
- 利用者が依頼したのは仕様の作成で、仕様の中身は承認されていない（``approval`` は ``not_approved``、判断事項はどれも ``pending``。--check が確かめる）。
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "diagnostics-replay-api-design.json"
DESIGN = ROOT / "docs" / "diagnostics-replay-api-design.md"
PLAN = ROOT / "docs" / "diagnostics-replay-api-implementation-plan.md"
LEDGER = ROOT / "docs" / "stop-policy-classification.json"
RECORDS = ROOT / "kyuura_engine" / "data" / "convention_records.json"

ROLES = ("actor", "opponent", "spectator", "verifier")
VISIBILITY = ("yes", "no", "own", "decider", "derived")  # own: 本人に関わるものだけ。decider: 決めるプレイヤーだけ。derived: 観測・ログの写しを通した形だけ
CATEGORIES = ("invalid_input", "unresolved_ruling", "unsupported", "technical_limit", "state_integrity", "compatibility", "internal_error", "unmapped")
OUTCOMES = ("accepted", "rejected", "failed")
STATUSES = ("in_progress", "awaiting_decision", "halted", "game_over", "sudden_death_pending", "not_started", "unavailable")
FEATURE_STATUS = ("implemented", "internal_only", "tool_only", "not_implemented")
ADAPTER_IDS = ("DIAGNOSTIC_UNMAPPED", "INTERNAL_ERROR", "SUBMITTER_MISMATCH", "INVALID_SEED")
REPLAY_STATUS = ("succeeded", "incomplete", "unsupported", "invalid_record", "diverged", "internal_error")
NEW_VERSION_KEYS = ("kyuura_diagnostic_schema", "kyuura_replay_format", "kyuura_view_format", "kyuura_snapshot_format")
EXISTING_VERSION_KEYS = ("format_version", "record_format", "digest_format", "engine_version", "version")
VERIFIER_ONLY_FIELDS = ("developer_detail", "seed", "rng_state", "rng_fingerprint", "state_digest", "initial_deck_order", "halt_message", "trace", "engine_code",
                        "raw_message", "traceback", "problems", "exception_type")

ADOPTION = {
    "id": "ADOPT-U1-U2",
    "date": "2026-11-06",
    "by": "利用者",
    "scope": "U1（診断の型と情報境界）と U2（コマンド実行結果のアダプタ）の実装と、次の方針だけ。仕様案のほかの判断事項・仕様案の全体の承認ではない",
    "policies": [
        "本人向けの説明は、原則としてコードに対応する安全な定型文とする",
        "生の例外文と内部の詳細は検証者用とし、通常の閲覧者へ渡さない",
        "状態の不整合は、本人にも一般的な説明だけを返す",
        "未登録コードを推測で未裁定・未対応へ分類しない。診断の対応漏れとして検出する",
        "拒否された操作は、将来の完全記録へ任意で残せる設計にする。受理した操作の再現とは区別する",
        "対戦後も情報の公開範囲を自動では広げない",
    ],
    "decisions": ["D-MESSAGE", "D-STATE-INTEGRITY-VIEW", "D-REJECTED", "D-POSTGAME"],
    "units": ["U1", "U2"],
    "implemented_in": "v0.152（docs/diagnostics-adapter-v0.152.md）",
}

BASE = {
    "commit": "7e4a875681f15745cfe42a2b95c00f0e4f557324",
    "engine_version": "0.151.0",
    "published_on": "origin/claude/deck-search-stop-oracles（v0.151 の最後。2026-11-06 に fetch して確かめた）",
    "origin_main": "8d4beffd9e4cc77367df8a4eae1657c04ca824d0",
    "origin_main_is_ancestor": True,
}

SPEC = {
    "schema_version": 1,
    "title": "診断 API と対戦記録・再現インターフェースの仕様案",
    "status": "proposed",
    "approval": "not_approved",
    "request": ("利用者の依頼（2026-11-06）は、v0.151 までの山札をさがす効果の情報漏れの監査を踏まえた仕様の作成。エンジンの動作・API・保存と復元の実装、続行規約の採用はしない。"
                "仕様の作成の依頼を、仕様の中身の承認として扱わない"),
    "base": BASE,
    "adoptions": [ADOPTION],
    "documents": {"design": "docs/diagnostics-replay-api-design.md", "plan": "docs/diagnostics-replay-api-implementation-plan.md",
                  "generator": "scripts/build_diagnostics_replay_api_design.py", "test": "tests/test_diagnostics_replay_api_design.py"},
    "sources": {"stop_ledger": "docs/stop-policy-classification.json", "scene_index": "kyuura_engine/data/convention_records.json"},

    # ------------------------------------------------------------ 既存の機能（実装済み・内部の入口・検証用の道具だけ・未実装）
    "existing": [
        {"id": "EX-APPLY-COMMAND", "name": "コマンドの入口 apply_command", "status": "implemented",
         "refs": ["kyuura_engine/engine.py::apply_command", "kyuura_engine/errors.py::EngineError"],
         "provides": "状態を複製して処理し、新しい状態を返す。EngineError（拒否）では渡した状態・乱数・ログを変えない（errors.py の約束）",
         "reuse": "コマンド実行結果のアダプタ（U2）は、これを包むだけにする。受理・拒否の判定をアダプタで作り直さない",
         "limits": "結果は例外か状態。分類・処理段階・見る人ごとの写しはない。EngineError でない例外（RuntimeError など）は、そのまま上に出る"},
        {"id": "EX-ERRORS", "name": "例外の種類とコード", "status": "implemented",
         "refs": ["kyuura_engine/errors.py::IllegalActionError", "kyuura_engine/errors.py::UnsupportedError", "kyuura_engine/errors.py::StateIntegrityError",
                  "kyuura_engine/errors.py::DeckValidationError", "kyuura_engine/conventions.py::ConventionSetError", "kyuura_engine/errors.py::HiddenPropertyRead"],
         "provides": "code（短い名前）と message（説明の文）。UnsupportedError は未裁定（UNRESOLVED_）・未対応（UNSUPPORTED_）・技術的制限・互換性の拒否をまとめて表す",
         "reuse": "診断の code はこの code をそのまま使う。分類は例外の種類だけで決めず、台帳の分類と合わせて決める（classification_rules）",
         "limits": "UnsupportedError の中の区別（未裁定・未対応・上限・互換性）は例外の種類からは分からない。事例（case）を例外が持たない"},
        {"id": "EX-HALT", "name": "停止（HALTED）と途中停止の記録", "status": "implemented",
         "refs": ["kyuura_engine/state.py::Phase", "kyuura_engine/state.py::Halt", "kyuura_engine/state.py::Interruption", "kyuura_engine/interruption.py::public_record"],
         "provides": "どの操作でも避けられない停止は、拒否ではなく HALTED の状態を返す（halt.code・message・references・interruption）。ログ halted はコードだけを全員に見せる",
         "reuse": "操作の結果が停止になった場合（status=halted）の診断は、halt.code・interruption の公開の記録から作る",
         "limits": "HALTED は終端で、再開する API はない（GAP-DEFERRED-HALT-NO-RESUME）。halt.message は診断用の文で観測に入らない"},
        {"id": "EX-DECISION", "name": "保留中の決定と観測の決定", "status": "implemented",
         "refs": ["kyuura_engine/state.py::PendingDecision", "kyuura_engine/observation.py::_decision", "kyuura_engine/commands.py::ResolveDecision"],
         "provides": "決定の id・種類・決めるプレイヤー・選ぶ数は全員に、選べるものは決めるプレイヤーにだけ見せる",
         "reuse": "status=awaiting_decision の診断と、閲覧用記録の決定は、観測の決定の形をそのまま使う",
         "limits": "resume・context は内部の続きの情報（観測に入らない）"},
        {"id": "EX-OBSERVE", "name": "観測とログの写し", "status": "implemented",
         "refs": ["kyuura_engine/observation.py::observe", "kyuura_engine/observation.py::visible_log", "kyuura_engine/observation.py::visible_segment_logs",
                  "kyuura_engine/observation.py::visible_event"],
         "provides": "見る人（0・1・観戦者 None）ごとの盤面とログ。知らないイベントの種類は ValueError（黙って全部を見せない）",
         "reuse": "閲覧用記録（B）は、観測とログの写しから作る。新しい見える範囲の表を作らない",
         "limits": "持ち主が知っているデッキリスト・所有者の変更は観測に入らない（v0.137 の owned_card_ids は検査の道具）。拒否された操作は状態を変えないので、ログにもない"},
        {"id": "EX-STATE-EXPORT", "name": "状態の書き出し（形式 1〜35）", "status": "implemented",
         "refs": ["kyuura_engine/serialize.py::state_to_dict", "kyuura_engine/serialize.py::FORMAT_VERSIONS"],
         "provides": "内部の完全な記録の書き出し（一方向）。形式 35 はエンジンの版と規約集合の識別を持つ。seed と乱数の状態の指紋（rng_state_sha256）を含む",
         "reuse": "再現用記録（A）の歩ごとの確認値（状態の指紋）に使う（engine_lockstep と同じ）",
         "limits": "書き出しから状態をもどす関数はない。乱数の状態そのものは入らない。形式 35 が状態を落とさず表すことは確かめていない。プレイヤーに渡してはいけない"},
        {"id": "EX-RNG-JSON", "name": "乱数の状態の保存・復元", "status": "implemented",
         "refs": ["kyuura_engine/rng.py::rng_state_to_json", "kyuura_engine/rng.py::rng_from_json", "kyuura_engine/rng.py::rng_fingerprint", "kyuura_engine/rng.py::RNG_FORMAT"],
         "provides": "メルセンヌ・ツイスタの状態の JSON と、知らない形式の拒否",
         "reuse": "状態スナップショット（C）の乱数の部分に使う",
         "limits": "状態全体の復元には使われていない"},
        {"id": "EX-PICKLE", "name": "Python の状態の写し（pickle・clone）", "status": "internal_only",
         "refs": ["kyuura_engine/state.py::GameState", "kyuura_engine/state.py::__setstate__"],
         "provides": "前の版の写しを後の版で読む向きの互換（項目の既定値）",
         "reuse": "再利用しない（保存の形式にしない）",
         "limits": "安全な外部のデータ交換の形式ではない。後の版の写しを前の版で読む向きは約束しない"},
        {"id": "EX-CONVENTION-ID", "name": "規約集合の識別と確かめ", "status": "implemented",
         "refs": ["kyuura_engine/conventions.py::ConventionSetIdentity", "kyuura_engine/conventions.py::resolve_for_new_game",
                  "kyuura_engine/conventions.py::require_state_conventions", "kyuura_engine/conventions.py::legacy_problems"],
         "provides": "集合 ID・版・照合値・区分・完全性・構成の規約。状態の集合を扱えなければ UNSUPPORTED_CONVENTION_SET",
         "reuse": "すべての記録の見出しと、再現の前の確かめに、record() の形をそのまま使う",
         "limits": "照合値は内容の識別で、署名・認証ではない"},
        {"id": "EX-COMMAND-CODEC", "name": "コマンドの辞書への変換", "status": "implemented",
         "refs": ["kyuura_engine/commands.py::command_to_dict", "kyuura_engine/commands.py::command_from_dict"],
         "provides": "知らない種類は UNKNOWN_COMMAND、足りない・余分な項目は BAD_COMMAND",
         "reuse": "再現用記録の操作の列の形にする",
         "limits": "コマンドの選んだ値（山札のカードの uid など）は秘密の情報を含みうる（閲覧用記録には入れない）"},
        {"id": "EX-RESUME-GUARD", "name": "知らない再開先・前の版の決定の拒否", "status": "implemented",
         "refs": ["kyuura_engine/engine.py::supported_decision_error", "kyuura_engine/decisions.py::unsupported_decision_error", "kyuura_engine/decisions.py::RETIRED_DECISIONS"],
         "provides": "観測・コマンドの前に UNSUPPORTED_DECISION。続けるのに要る情報が欠ける状態は StateIntegrityError",
         "reuse": "スナップショットの復元（U6）の確かめに、同じ入口を使う",
         "limits": "前の版（v0.139 以前）の動きは変えられない"},
        {"id": "EX-SUDDEN-DEATH", "name": "サドン・デスの区間", "status": "implemented",
         "refs": ["kyuura_engine/commands.py::StartSuddenDeath", "kyuura_engine/state.py::SegmentRecord", "kyuura_engine/engine.py::_start_sudden_death",
                  "kyuura_engine/sudden_death.py::archive"],
         "provides": "延長戦を始めると、前の区間のログ・結果・所有者の変更を segments に移す。乱数は前の区間から続ける（seed にもどさない）",
         "reuse": "記録の区間の境界は StartSuddenDeath の歩と segments の番号で表す",
         "limits": "区間の記録の検査（segment_problems）と延長戦を通す対戦は検証用の道具（tools/sudden_death_games.py）"},
        {"id": "EX-LOCKSTEP", "name": "1 歩ごとの記録と比べ（engine_lockstep）", "status": "tool_only",
         "refs": ["tools/engine_lockstep.py::Recorder", "tools/engine_lockstep.py::RECORD_FORMAT", "tools/engine_lockstep.py::DIGEST_EXCLUDED"],
         "provides": "見出し（record_format 2・digest_format・規約集合）と歩ごとの記録（コマンドの指紋・受理か拒否の種類とコードと理由の文の指紋・状態の指紋 h・規約集合の指紋 k）。"
                     "集合の違う記録の比べは --cross-set で別扱い（終了コード 3）",
         "reuse": "再現用記録（A）の歩の記録の項目と、版・規約集合をまたぐ比べ（U4 の compare_runs）は、この形と契約を元にする",
         "limits": "コマンドは指紋だけ（コマンドそのものがないので記録から再実行できない）。対戦は方策（play_game・choose_command）を再実行して作る。ふだんのテストでは走らない"},
        {"id": "EX-LOG-AUDIT", "name": "ログの監査", "status": "tool_only",
         "refs": ["tests/log_audit.py::log_problems"],
         "provides": "new_game から進めたログだけから場を組み立て直し、状態と同じかを確かめる",
         "reuse": "再現の検証（verify_record）の追加の確かめとして呼べる候補",
         "limits": "テストの道具（パッケージに入っていない）"},
        {"id": "EX-TWIN-AUDIT", "name": "双子の比較（拒否による情報漏れ）", "status": "tool_only",
         "refs": ["tests/log_audit.py::twin_command_problems", "tests/log_audit.py::command_outcome", "tests/log_audit.py::public_view", "tests/log_audit.py::owned_card_ids"],
         "provides": "公開の情報が同じで見えない配分だけが違う状態に同じ操作を送り、受理・拒否・コード・理由の文が変わらないかを比べる",
         "reuse": "診断の写し（見る人ごと）が配分によらないことの回帰テスト（U1・U2）に使う",
         "limits": "テストの道具。双子を作る swap_hidden・swap_set_aside は各版のテストにある"},
        {"id": "EX-STOP-LEDGER", "name": "停止の方針の台帳と場面の索引", "status": "implemented",
         "refs": ["docs/stop-policy-classification.json", "kyuura_engine/data/convention_records.json", "kyuura_engine/conventions.py::scenes_for_code",
                  "kyuura_engine/conventions.py::continuation_lookup"],
         "provides": "停止コードごとの分類（A エンジン機能不足・B 技術的制限・C 未裁定・E 内部ガードなど）・止め方・事例（コード#事例）。同梱の索引はコードから場面を引く",
         "reuse": "診断の分類と事例 ID の元にする（新しいコード表を手で作らない）",
         "limits": "台帳は文書で、エンジンは実行中に読まない（同梱の場面の索引だけを読む）。事例を特定できるのは事例が 1 つのコードか、照会で事例を渡す場所だけ"},
        {"id": "EX-TRACE", "name": "解決の記録（内部の入口）", "status": "internal_only",
         "refs": ["kyuura_engine/engine.py::apply_command_traced"],
         "provides": "ワザ・番の終わりの解決の記録（先読みの枝を含む）。状態に保存しない",
         "reuse": "開発用の詳細（developer_detail）の候補。検証者だけ",
         "limits": "公開の API ではない。秘密の配分を含む"},
        {"id": "NI-STATE-RESTORE", "name": "状態の読み込み（state_from_dict など）", "status": "not_implemented", "refs": [],
         "provides": "ない（v0.1 から未実装）", "reuse": "U6 で新しく作る", "limits": "形式 35 を読み込み用に読み替えない"},
        {"id": "NI-LEGAL-MOVES", "name": "合法手の一覧", "status": "not_implemented", "refs": ["tools/stress_engine.py::choose_command"],
         "provides": "ない（ストレス実行の操作の選び方は検証用の道具で、合法手の一覧ではない）", "reuse": "U7 で境界だけを決める", "limits": "でたらめな操作を混ぜる道具"},
        {"id": "NI-DIAGNOSTIC", "name": "構造化した診断（v0.152 で U1・U2 として実装）", "status": "implemented",
         "refs": ["kyuura_engine/diagnostics.py::classify_error", "kyuura_engine/adapter.py::submit", "kyuura_engine/data/diagnostic_catalog.json",
                  "scripts/build_diagnostic_catalog.py"],
         "provides": "コード表による分類・見る人ごとの結果（本人・相手と観戦者）・検証者用の記録・コマンド実行結果のアダプタ（v0.152）",
         "reuse": "U3 以後の記録・再現は submit の結果（CommandResult）を受け取る", "limits": "記録・再現・合法手の一覧はない"},
        {"id": "NI-REPLAY-RECORD", "name": "完全な再現用記録と再現", "status": "not_implemented", "refs": ["tests/helpers.py::replay"],
         "provides": "ない（テストの replay はコマンドの列を順に送るだけ）", "reuse": "U3・U4 で作る", "limits": ""},
        {"id": "NI-VIEW-RECORD", "name": "閲覧用記録", "status": "not_implemented", "refs": [],
         "provides": "ない（観測・ログの写しの部品はある）", "reuse": "U5 で作る", "limits": ""},
        {"id": "NI-HALT-RESUME", "name": "停止からの再開", "status": "not_implemented", "refs": [],
         "provides": "ない（GAP-DEFERRED-HALT-NO-RESUME）", "reuse": "この仕様の範囲の外（続行規約の採用は別の判断）", "limits": ""},
    ],

    # ------------------------------------------------------------ 診断の分類
    "categories": [
        {"id": "invalid_input", "label": "不正な操作・不正な回答・不正な開始の条件",
         "sources": "IllegalActionError（すべてのコード）、DeckValidationError（INVALID_DECK）、ConventionSetError（INVALID_CONVENTION_SET）、アダプタが new_game の前に確かめる seed の型・範囲",
         "subkinds": ["command", "answer", "setup"], "state_effect": "渡した状態・乱数・ログは変わらない", "continuable": True,
         "note": "ルール上・形式上できない操作。同じ状態に同じ操作を送ると同じ拒否になる（乱数を使わない）"},
        {"id": "unresolved_ruling", "label": "未裁定による停止",
         "sources": "台帳の分類 C のコード（UNRESOLVED_ の研究上の停止・コードのない問い）と UNRESOLVED_RULING。UnsupportedError の拒否か、HALTED の halt.code",
         "subkinds": [], "state_effect": "拒否なら状態は変わらない。HALTED なら、そこまでの処理を残した終端の状態", "continuable": True,
         "note": "研究上の未解決。エンジンの未対応と区別する。続行規約がある集合では止まらない（その場面だけ）"},
        {"id": "unsupported", "label": "未対応・未実装",
         "sources": "台帳の分類 A のコード（UNSUPPORTED_ のうち互換性・技術的制限でないもの）、UNSUPPORTED_CARD（デッキの検査）",
         "subkinds": [], "state_effect": "拒否なら状態は変わらない。HALTED なら終端", "continuable": True,
         "note": "ルールとしてはありうるが、このエンジンが処理しない。効果がないものとして進めない"},
        {"id": "technical_limit", "label": "技術的制限・探索上限",
         "sources": "台帳の分類 B のコード（UNSUPPORTED_PREFLIGHT_LIMIT・UNSUPPORTED_SECRET_PLAN_IDENTITIES など）と、上限の項目（LIMIT:*）",
         "subkinds": [], "state_effect": "状態は変わらない", "continuable": True,
         "note": "上限は公開の情報だけで決まる（v0.117 の約束）。上限を超えたことから秘密の情報を推測できないことを、上限ごとに確かめる"},
        {"id": "state_integrity", "label": "状態の不整合",
         "sources": "StateIntegrityError（STATE_INTEGRITY）。処理の前の入力の確かめ（壊れた状態・情報の足りない状態）と処理の後の不変条件",
         "subkinds": ["input", "result"], "state_effect": "渡した状態は変わらないが、その状態で続けることは保証しない", "continuable": False,
         "note": "エンジンの不具合か、呼び出し側が状態を書き換えたか、前の版の写し。どれかを状態から決めない"},
        {"id": "compatibility", "label": "未知・非対応の規約集合や互換性",
         "sources": "UNSUPPORTED_CONVENTION_SET・UNSUPPORTED_DECISION・UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN（前の版の記録）と、記録・スナップショットの知らない形式・項目・版",
         "subkinds": ["conventions", "decision", "legacy_state", "record_format"], "state_effect": "状態は変わらない", "continuable": False,
         "note": "この実装ではその状態・記録を扱えない。推測で読み替えない"},
        {"id": "internal_error", "label": "内部エラー",
         "sources": "EngineError でない例外（RuntimeError・ValueError・KeyError・TypeError など。不変条件の RuntimeError を含む）",
         "subkinds": [], "state_effect": "保証しない（apply_command は複製で処理するが、内部エラーについては約束していない）", "continuable": False,
         "note": "未対応・未裁定に変換しない。開発用の詳細は検証者だけに渡し、ほかの見る人には分類だけを返す"},
        {"id": "unmapped", "label": "診断の対応漏れ（v0.152 の採用）",
         "sources": "コード表にないコード・表と違う例外の型で来たコード（EngineError）、表にない停止のコード",
         "subkinds": [], "state_effect": "EngineError なので渡した状態は変わらない（拒否）。停止のコードなら受理した結果の停止", "continuable": True,
         "note": "接頭辞・例外の型の名前から未裁定・未対応へ推測で分類しない。元のコードは検証者用の記録だけに置き、表の生成の検査（--check）とテストで漏れを見つける"},
    ],
    "classification_rules": [
        {"order": 1, "when": "EngineError でない例外", "category": "internal_error", "basis": "例外の型（EngineError の子でない）"},
        {"order": 2, "when": "StateIntegrityError", "category": "state_integrity", "basis": "例外の型"},
        {"order": 3, "when": "UnsupportedError で、コードが互換性の表（compatibility_codes）にある", "category": "compatibility", "basis": "コード"},
        {"order": 4, "when": "IllegalActionError・DeckValidationError（INVALID_DECK）・ConventionSetError", "category": "invalid_input",
         "basis": "例外の型。subkind は、決定への答え（ResolveDecision・TakePrize・PromoteActive・ReportJankenResult）なら answer、new_game の前なら setup、ほかは command"},
        {"order": 5, "when": "UnsupportedError・HALTED の halt.code・デッキの検査の UNSUPPORTED_CARD で、台帳の分類が C（または UNRESOLVED_RULING）", "category": "unresolved_ruling",
         "basis": "台帳の分類（接頭辞だけで決めない）"},
        {"order": 6, "when": "同じく、台帳の分類が B", "category": "technical_limit", "basis": "台帳の分類"},
        {"order": 7, "when": "同じく、台帳の分類が A・E（UNSUPPORTED_CARD を含む）", "category": "unsupported", "basis": "台帳の分類"},
        {"order": 8, "when": "EngineError で、コード表にないコード、または表の行の例外の型の区分（raised_as）と合わない", "category": "unmapped",
         "basis": "v0.152 の採用（推測で分類しない）。コード表は台帳と台帳の外のコード（不正な操作・状態の不整合など）を合わせたもので、台帳には加えない"},
    ],
    "compatibility_codes": ["UNSUPPORTED_CONVENTION_SET", "UNSUPPORTED_DECISION", "UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN"],
    "unresolved_generic_codes": ["UNRESOLVED_RULING"],
    "outcomes": [
        {"id": "accepted", "meaning": "操作を受け付けた。新しい状態に置きかわる（乱数・ログが進むことがある）", "state": "new", "categories": [],
         "next": "結果の status による（in_progress・awaiting_decision・halted・game_over・sudden_death_pending）"},
        {"id": "rejected", "meaning": "操作を拒否し、元の状態を保った（状態・乱数・ログは変わらない）", "state": "kept",
         "categories": ["invalid_input", "unresolved_ruling", "unsupported", "technical_limit", "compatibility", "unmapped"],
         "next": "同じ状態に別の操作を送れる（compatibility なら、この実装ではどの操作も同じ拒否）。同じ操作は同じ拒否になる"},
        {"id": "failed", "meaning": "処理できなかった。元の状態で続けることを保証しない", "state": "untrusted", "categories": ["state_integrity", "internal_error"],
         "next": "対戦を止め、検証者が調べる（自動で続けない）"},
    ],
    "statuses": [
        {"id": "in_progress", "meaning": "番のプレイヤーの操作を待つ（準備の段階を含む）", "public": True},
        {"id": "awaiting_decision", "meaning": "決定への答えを待つ（決定の id・種類・決めるプレイヤー・選ぶ数は全員に見え、選べるものは決めるプレイヤーだけ）", "public": True},
        {"id": "halted", "meaning": "操作の結果として停止した（終端。halt.code は全員に見え、途中停止なら interruption の公開の記録がある。再開の API はない）", "public": True},
        {"id": "game_over", "meaning": "勝ち負けが決まった（終端）", "public": True},
        {"id": "sudden_death_pending", "meaning": "サドン・デスに移り、延長戦を始める操作（StartSuddenDeath）だけを受け付ける", "public": True},
        {"id": "not_started", "meaning": "対戦を始める前の拒否（start_game。状態はない。v0.152）", "public": True},
        {"id": "unavailable", "meaning": "処理できなかった結果（failed）。状態を返さない（v0.152）", "public": True},
    ],
    "stages": [
        {"id": "setup", "meaning": "new_game・準備（切り直し・ポケモンを出す・ジャンケン）"},
        {"id": "turn_action", "meaning": "番の操作の宣言（ワザ・トレーナー・特殊能力・にげる・エネルギー・番の終わりなど）の受付と、宣言の前の先読み（v0.152 の名前。仕様案の action_declaration・between_turns をまとめた）"},
        {"id": "decision_answer", "meaning": "保留中の決定への答え（決定の種類・処理の段階は決定の kind と、本人に見える context から）"},
        {"id": "segment_start", "meaning": "サドン・デスの延長戦を始める操作"},
        {"id": "state_check", "meaning": "観測・コマンドの前の状態の確かめ（規約集合・再開先）。将来のスナップショットの復元もここ"},
        {"id": "submission", "meaning": "ホストが確かめた送り手とコマンドのプレイヤーの照合（v0.152。エンジンを呼ぶ前）"},
        {"id": "record_check", "meaning": "記録の形式・見出し・依存の確かめ（再現の前。U3 以後）"},
    ],

    # ------------------------------------------------------------ 診断の項目
    "diagnostic_fields": [
        {"field": "kyuura_diagnostic_schema", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "診断の形の版（整数。v0.152 は 1）"},
        {"field": "role", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "actor（本人への結果）・observer（相手・観戦者への今の状態の知らせ）"},
        {"field": "viewer", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "見る人（0・1・null）"},
        {"field": "outcome", "stability": "fixed", "required": True, "audience": "actor", "meaning": "accepted・rejected・failed（本人だけ）"},
        {"field": "status", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "操作のあとの状態（statuses の語彙）"},
        {"field": "stage", "stability": "fixed", "required": True, "audience": "actor", "meaning": "送った操作の処理段階（コマンドの種類と公開の段階から決まる）"},
        {"field": "continuable", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "実際の状態で、この版が次の操作を処理しうるか（分類から推測しない）"},
        {"field": "next", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "次に受け付けうる操作の種類と送るプレイヤー（合法手の一覧ではない）"},
        {"field": "diagnostic_id", "stability": "fixed", "required": True, "audience": "actor",
         "meaning": "API として安定した診断の識別。コード表で対応付けたコードはそのコード、アダプタが作るものは DIAGNOSTIC_UNMAPPED・INTERNAL_ERROR・SUBMITTER_MISMATCH・INVALID_SEED"},
        {"field": "category", "stability": "fixed", "required": True, "audience": "actor", "meaning": "診断の分類（accepted なら null）"},
        {"field": "subkind", "stability": "fixed", "required": False, "audience": "actor", "meaning": "不正な入力の区分（command・answer・setup）"},
        {"field": "case_id", "stability": "fixed", "required": False, "audience": "actor", "meaning": "コードの場面が 1 つのときの事例 ID。2 つ以上なら null"},
        {"field": "case_status", "stability": "fixed", "required": True, "audience": "actor", "meaning": "identified・not_identified・not_applicable"},
        {"field": "message", "stability": "explanatory", "required": False, "audience": "actor", "meaning": "コードに対応する安全な定型文（埋め込みなし。v0.152 の採用）。プログラムで判定しない"},
        {"field": "halt", "stability": "fixed", "required": False, "audience": "viewer", "meaning": "停止した状態の公開の診断（識別・分類・事例・停止の定型文・途中停止か）"},
        {"field": "operation_id", "stability": "fixed", "required": False, "audience": "actor", "meaning": "ホストが付けた操作の識別（将来の記録との対応。本人だけ）"},
        {"field": "convention_set", "stability": "fixed", "required": True, "audience": "viewer", "meaning": "適用中の規約集合の ID・版・照合値"},
        {"field": "engine_code", "stability": "fixed", "required": False, "audience": "verifier", "meaning": "エンジンが返した元のコード（対応漏れのときも）"},
        {"field": "raw_message", "stability": "explanatory", "required": False, "audience": "verifier", "meaning": "例外の生の文"},
        {"field": "traceback", "stability": "explanatory", "required": False, "audience": "verifier", "meaning": "例外の traceback"},
        {"field": "problems", "stability": "explanatory", "required": False, "audience": "verifier", "meaning": "状態の不整合の問題の文"},
        {"field": "halt_message", "stability": "explanatory", "required": False, "audience": "verifier", "meaning": "停止の診断用の文・references"},
        {"field": "command", "stability": "explanatory", "required": False, "audience": "verifier", "meaning": "送ったコマンド（command_to_dict）"},
    ],

    # ------------------------------------------------------------ 情報境界（見る人ごと）
    "roles": [
        {"id": "actor", "meaning": "操作する本人（決定への答えなら決めるプレイヤー）", "holder": "プレイヤーの画面・AI。状態を持たない"},
        {"id": "opponent", "meaning": "相手のプレイヤー", "holder": "プレイヤーの画面・AI。状態を持たない"},
        {"id": "spectator", "meaning": "観戦者（observe の viewer=None）", "holder": "観戦の画面。状態を持たない"},
        {"id": "verifier", "meaning": "完全な情報を扱う検証者（開発・不具合調査・審判役）",
         "holder": "状態・完全な記録を持つ側（対戦を進める権限の側か、その写しを受け取った調査の環境）。見る人の値ではなく、完全な状態を持っていることが権限"},
    ],
    "visibility": [
        {"item": "diagnostic.outcome（拒否された操作）", "group": "diagnostic", "actor": "yes", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "拒否は状態を変えずログにも残らない。相手に試した操作を知らせない（本人の手札などを含む操作の内容が漏れる）"},
        {"item": "diagnostic.category・code・subkind・stage", "group": "diagnostic", "actor": "yes", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "受理・拒否と同じ境界（v0.135〜v0.151 の双子の比較の対象）"},
        {"item": "diagnostic.case_id", "group": "diagnostic", "actor": "yes", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "事例は止まった場所（コードの区別）で決まり、秘密の配分で決めない。配分で事例が変わる場所は事例を出さない（not_identified）"},
        {"item": "diagnostic.message", "group": "diagnostic", "actor": "yes", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "コードに対応する安全な定型文だけ（v0.152 の採用。D-MESSAGE）。生の文は検証者用"},
        {"item": "diagnostic.developer_detail・detail_ref", "group": "diagnostic", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "例外の生の文・halt.message・解決の記録は実際の配分を含みうる"},
        {"item": "halt.code（停止した状態）", "group": "diagnostic", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "ログ halted と同じ（全員に見えるイベント）"},
        {"item": "halt.message・references", "group": "diagnostic", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "診断用の文（観測に入らない）"},
        {"item": "interruption の公開の記録", "group": "diagnostic", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "interruption.public_record（全員に見える項目だけ）"},
        {"item": "internal_error の分類", "group": "diagnostic", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "対戦が止まったことは全員に分かる。内容は検証者だけ"},
        {"item": "decision.id・kind・player・選ぶ数", "group": "decision", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "observation._decision と同じ"},
        {"item": "decision.options（選べるもの）", "group": "decision", "actor": "decider", "opponent": "decider", "spectator": "no", "verifier": "yes",
         "basis": "決めるプレイヤーにだけ（見えるカードにだけ id を添える）"},
        {"item": "decision.resume・context", "group": "decision", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "内部の続きの情報"},
        {"item": "受理した操作（コマンドそのもの）", "group": "record", "actor": "own", "opponent": "derived", "spectator": "derived", "verifier": "yes",
         "basis": "選んだ値に山札・手札のカードの uid が入りうる。ほかの人にはログの写し（visible_log）で見せる"},
        {"item": "拒否された操作の列", "group": "record", "actor": "own", "opponent": "no", "spectator": "no", "verifier": "yes", "basis": "診断と同じ"},
        {"item": "ログ（イベント）", "group": "record", "actor": "derived", "opponent": "derived", "spectator": "derived", "verifier": "yes",
         "basis": "visible_log・visible_segment_logs の写し（PRIVATE_FIELDS の見える人）"},
        {"item": "コインの結果", "group": "record", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "投げたあとのログ coin_flip（全員）。再現の入力にはしない（seed から決まる確認値）"},
        {"item": "デッキリスト", "group": "record", "actor": "own", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "持ち主は自分で出したので知っている。相手のデッキリストは公開されない（対戦後の公開は D-POSTGAME）"},
        {"item": "初期の山札の並び・サイドの中身", "group": "record", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "見えない情報（並びから未来に引くカードが分かる）"},
        {"item": "seed", "group": "record", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "ログ game_created の seed はだれにも見せない（_nobody）。seed から山札の並び・コインが分かる"},
        {"item": "乱数の状態・乱数の指紋（rng_state_sha256）", "group": "record", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "指紋でも、小さな seed を総当たりで確かめて未来のコイン・山札を予測できる"},
        {"item": "完全な状態の指紋（形式 35 の sha256）", "group": "record", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "見えない配分の候補を当てはめて指紋と比べれば、推測を確かめられる（サイドの中身など、候補の少ない秘密）"},
        {"item": "完全な状態・形式 35 の書き出し・pickle", "group": "record", "actor": "no", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "内部の完全な記録（observation の説明）"},
        {"item": "規約集合の識別", "group": "record", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "observe の convention_set（全員に見える）"},
        {"item": "エンジンの版・実装の識別", "group": "record", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "秘密の情報を含まない。両方が同じ実装で対戦していることを確かめられる"},
        {"item": "区間の結果・番号・サイドの枚数", "group": "record", "actor": "yes", "opponent": "yes", "spectator": "yes", "verifier": "yes",
         "basis": "observe の segment（全員）"},
        {"item": "AI・道具の方策の名前と方策用の種", "group": "record", "actor": "own", "opponent": "no", "spectator": "no", "verifier": "yes",
         "basis": "エンジンの乱数とは別。再現の入力にしない（参考の記録）。相手に渡すと方策の手を予測できる"},
    ],
    "principles": [
        {"id": "P-REJECT-SPLIT", "rule": "受理・拒否・診断の分類・コード・事例・本人への文は、秘密の領域（山札・うらのサイド・見えない置いておくカード）への配分で変わらない",
         "origin": "v0.135〜v0.151（双子の比較）", "check": "U1・U2 の回帰テストで、診断の写しを twin_command_problems で比べる"},
        {"id": "P-PRESEARCH", "rule": "山札をさがす前の診断は、本人の知る情報（山札にあるかもしれないカード・配分を読まない下限・公開の枚数）だけで作る",
         "origin": "v0.147・v0.148・v0.151", "check": "診断を作る関数は、確かめの関数が返した結果だけを使い、実際の山札を読み直さない"},
        {"id": "P-POSTSEARCH", "rule": "さがし始めたあとに本人が正当に見た山札の内容（決定の選べるもの・見たカード）は、本人の診断・決定に使える",
         "origin": "v0.150・v0.151", "check": "決定の選べるものの見える範囲は observation._decision に従う"},
        {"id": "P-DEV-DETAIL", "rule": "開発用の詳細（生の文・halt.message・解決の記録・実装の場所）は検証者だけに渡し、相手・観戦者に送らない", "origin": "この仕様",
         "check": "閲覧用の診断・記録の写しに developer_detail の項目がない（--check と U1 のテスト）"},
        {"id": "P-FULL-NOT-VIEW", "rule": "完全な状態・形式 35・完全な記録・スナップショットを、表示用の観測と混同しない（見る人に渡さない）", "origin": "v0.47 の観測の約束",
         "check": "閲覧用記録は観測・ログの写しだけから作る"},
        {"id": "P-NO-RECONSTRUCT", "rule": "閲覧用記録から完全な再現用記録を復元できるとは保証しない（復元できないことを目標にする）", "origin": "この仕様",
         "check": "閲覧用記録に seed・乱数・状態の指紋・相手のコマンドを入れない"},
        {"id": "P-NO-PREDICT", "rule": "未来の見えない情報を予測できる値（seed・乱数の状態とその指紋・完全な状態の指紋・初期の山札の並び）を、検証者のほかに配らない", "origin": "この仕様",
         "check": "visibility の表で検証者だけ（--check）"},
        {"id": "P-NO-FREE-REDO", "rule": "対戦を進める権限の側だけが状態を持つ。見る人は状態を持たず、コインの結果・見た秘密のあとで前の状態から操作をやり直せない",
         "origin": "apply_command が渡した状態を変えないことの裏側（v0.151 の「見たあとのやり直しをさせない」）", "check": "アダプタは古い状態への操作を受け付けない（U2 の完了基準）"},
        {"id": "P-NO-PROMOTION", "rule": "権限を引数で指定するだけで完全な情報に上がる API にしない（見る人の値に verifier を加えない）", "origin": "この仕様",
         "check": "完全な情報を返す関数は、完全な状態・完全な記録を引数に取るものだけ。見る人の値は 0・1・None のまま"},
        {"id": "P-INTERNAL-NOT-UNSUPPORTED", "rule": "内部エラーを未対応・未裁定に変換しない", "origin": "この仕様",
         "check": "分類の規則の 1 番目（--check と U1 のテスト）"},
    ],

    # ------------------------------------------------------------ 記録の種類
    "records": [
        {"id": "replay_full", "label": "A. 完全な再現用記録", "version_key": "kyuura_replay_format",
         "purpose": "不具合調査・検証・同一実行の再現", "holder": "検証者（対戦を進める権限の側）", "contains_secrets": True,
         "inputs": ["header.engine", "header.dependencies", "header.convention_set", "header.initial", "steps[].command（受理したもの）"],
         "expected": ["steps[].outcome", "steps[].check", "steps[].coins", "footer"],
         "fields": [
             {"name": "kyuura_replay_format", "required": True, "role": "format", "meaning": "記録の形式の版（整数。状態の形式・lockstep の record_format とは別の番号）"},
             {"name": "header.engine", "required": True, "role": "input", "meaning": "エンジンの版（__version__）と実装の識別（implementation_digest。D-IMPLEMENTATION-ID）"},
             {"name": "header.runtime", "required": True, "role": "environment", "meaning": "Python の実装と版（再現の保証の条件は D-RUNTIME）"},
             {"name": "header.dependencies", "required": True, "role": "input",
              "meaning": "ルールの組の id（RuleSet.id）・カードデータの写しの元（repository・commit・path）と内容の照合値・効果の登録表の id（state.effects.id）"},
             {"name": "header.convention_set", "required": True, "role": "input", "meaning": "ConventionSetIdentity.record（ID・版・照合値・構成）"},
             {"name": "header.initial", "required": True, "role": "input",
              "meaning": "デッキリスト 2 つ・seed・乱数の方式（rng.RNG_FORMAT と new_game の切り方）。初期の山札の並びは seed から決まるので入れない（入れるなら確認値）"},
             {"name": "header.game_id", "required": True, "role": "reference", "meaning": "対戦の識別（記録の中だけで一意）"},
             {"name": "header.policy", "required": False, "role": "reference", "meaning": "操作を選んだ AI・道具の名前と方策の乱数（参考。再現の入力にしない）"},
             {"name": "steps[].index・segment・actor", "required": True, "role": "input", "meaning": "送った順の番号・区間の番号・操作したプレイヤー"},
             {"name": "steps[].command", "required": True, "role": "input", "meaning": "command_to_dict の形。拒否された操作も記録する（D-REJECTED）が、再現の入力は受理したものだけ"},
             {"name": "steps[].decision_id", "required": False, "role": "expected", "meaning": "答えた決定の id（決定への答えのとき）"},
             {"name": "steps[].outcome", "required": True, "role": "expected", "meaning": "accepted・rejected・failed、例外の種類・コード・理由の文の指紋"},
             {"name": "steps[].check", "required": True, "role": "expected",
              "meaning": "受理した歩のあとの確認値: 状態の指紋（形式 35 の sha256。engine_version を除く）・ログの長さ・status・保留中の決定の id と種類（D-CHECK-DENSITY）"},
             {"name": "steps[].coins", "required": False, "role": "expected", "meaning": "その歩で投げたコインの結果（ログから取った確認値。入力ではない）"},
             {"name": "segments[]", "required": True, "role": "expected", "meaning": "区間の境界: 番号・始まった歩（StartSuddenDeath の歩）・サイドの枚数・終えた結果"},
             {"name": "footer", "required": True, "role": "expected",
              "meaning": "終わりの印: 終わった理由（game_over・halted・failed・abandoned）・歩の数・最後の状態の指紋。ないなら途中で切れた記録（incomplete）"},
         ],
         "guarantees": ["同じ実装・同じ依存・同じ規約集合・同じ初期の条件・同じ受理した操作の列から、各歩の確認値と同じ結果になる（U4 で確かめる）"],
         "not_guaranteed": ["実装・依存・規約集合が違うときの再現（比べは compare_runs の別の機能）", "seed だけからの、版をまたぐ再現",
                            "方策の再実行で同じ操作の列になること"]},
        {"id": "view", "label": "B. 本人・相手・観戦者向けの閲覧用記録", "version_key": "kyuura_view_format",
         "purpose": "画面の表示・対戦の履歴・共有", "holder": "見る人（プレイヤー・観戦者）", "contains_secrets": False,
         "inputs": [], "expected": [],
         "fields": [
             {"name": "kyuura_view_format", "required": True, "role": "format", "meaning": "閲覧用記録の形式の版"},
             {"name": "header.viewer", "required": True, "role": "reference", "meaning": "見る人（0・1・観戦者）"},
             {"name": "header.engine・convention_set", "required": True, "role": "reference", "meaning": "エンジンの版・実装の識別・規約集合の識別（全員に見える値）"},
             {"name": "header.own_decklist", "required": False, "role": "reference", "meaning": "プレイヤーの記録だけ。自分のデッキリスト"},
             {"name": "entries[].events", "required": True, "role": "reference", "meaning": "受理した操作ごとの visible_log の差分（区間ごとに visible_segment_logs）"},
             {"name": "entries[].decision", "required": False, "role": "reference", "meaning": "その時点の観測の決定（選べるものは決めるプレイヤーの記録だけ）"},
             {"name": "entries[].own_rejections", "required": False, "role": "reference", "meaning": "本人の記録だけ。本人が送って拒否された操作と、本人向けの診断"},
             {"name": "segments[]・result", "required": True, "role": "reference", "meaning": "区間の番号・結果・最後の結果（全員に見える）"},
         ],
         "guarantees": ["その見る人が対戦中に観測・ログの写しで見たものと同じ"],
         "not_guaranteed": ["完全な再現用記録・スナップショットの復元", "ほかの見る人の記録の作り直し"]},
        {"id": "snapshot", "label": "C. 状態スナップショット", "version_key": "kyuura_snapshot_format",
         "purpose": "将来の JSON の保存・復元による途中再開", "holder": "対戦を進める権限の側", "contains_secrets": True,
         "inputs": ["state（すべての項目）", "rng（rng_state_to_json）"], "expected": ["check"],
         "fields": [
             {"name": "kyuura_snapshot_format", "required": True, "role": "format", "meaning": "スナップショットの形式の版（形式 35 とは別の番号）"},
             {"name": "header.engine・dependencies・convention_set", "required": True, "role": "input", "meaning": "再現用記録の見出しと同じ識別"},
             {"name": "state", "required": True, "role": "input", "meaning": "状態のすべての項目（ログ・区間・決定の resume と context を含む）"},
             {"name": "rng", "required": True, "role": "input", "meaning": "乱数の状態そのもの（rng_state_to_json）"},
             {"name": "check", "required": True, "role": "expected", "meaning": "状態の指紋（復元のあとに同じ値になること）"},
             {"name": "origin", "required": False, "role": "reference", "meaning": "作った記録（game_id・歩の番号）"},
         ],
         "guarantees": ["同じ実装で復元して続けると、途中で保存しなかった場合と同じ結果になる（U6 で確かめる）"],
         "not_guaranteed": ["実装・規約集合が違う版での復元", "前の形式の自動移行", "HALTED からの再開"]},
    ],
    "record_common": ["エンジンの版と実装の識別", "規約集合の識別（ConventionSetIdentity.record）", "対戦の識別 game_id と区間の番号", "知らない形式・項目の拒否"],

    # ------------------------------------------------------------ 再現インターフェース
    "replay_functions": [
        {"id": "replay_from_start", "meaning": "記録の見出しの初期の条件から new_game を作り、受理した操作を順に送り直す（方策を再実行しない）", "uses": ["replay_full"],
         "results": ["succeeded", "incomplete", "unsupported", "invalid_record", "diverged", "internal_error"]},
        {"id": "verify_record", "meaning": "記録の形・見出し・依存を確かめ、再実行して各歩の確認値（受理・拒否・コード・状態の指紋・コイン・決定）と比べる。ログの監査は追加の確かめ",
         "uses": ["replay_full"], "results": ["succeeded", "incomplete", "unsupported", "invalid_record", "diverged", "internal_error"]},
        {"id": "resume_from_snapshot", "meaning": "スナップショットを復元し、確かめ（不変条件・規約集合・再開先）を通してから続きの操作を送る", "uses": ["snapshot", "replay_full"],
         "results": ["succeeded", "unsupported", "invalid_record", "diverged", "internal_error"]},
        {"id": "compare_runs", "meaning": "異なる版・規約集合の 2 つの記録を、同じ初期の条件・同じ操作の列で比べ、最初の差を返す（同一実行の再現とは別。成功を返さない）",
         "uses": ["replay_full"], "results": ["unsupported", "invalid_record", "diverged", "internal_error"]},
    ],
    "replay_results": [
        {"id": "succeeded", "meaning": "最後まで確認値と同じ（記録が完全）"},
        {"id": "incomplete", "meaning": "終わりの印のない記録で、ある歩までは同じ（どこまで確かめたかを返す。成功に数えない）"},
        {"id": "unsupported", "meaning": "記録の形式の版・実装・依存・規約集合・実行環境を、この実装が扱えない（理由の項目を返す）"},
        {"id": "invalid_record", "meaning": "記録の形が不正・項目が足りない・見出しと歩が合わない・番号が飛ぶ"},
        {"id": "diverged", "meaning": "最初に違った歩（区間・番号・操作）と比較項目（outcome・code・state_digest・coins・decision・status・log_length）と、記録の値・再実行の値"},
        {"id": "internal_error", "meaning": "再実行の中の内部エラー（diverged に変えない）"},
    ],
    "guarantee_scope": {
        "same": ["実装の識別（implementation_digest）", "依存のデータ（カードデータの照合値・効果の登録表の id・ルールの組）", "規約集合（ID・版・照合値）",
                 "初期の条件（デッキリスト・seed・乱数の方式）", "受理した操作の列"],
        "rng": "エンジンの乱数は state.rng の 1 本だけ（rng.py）。AI・道具が操作を選ぶ乱数は別で、記録の入力にしない（送った操作そのものを記録する）",
        "coins": "コインの結果は入力ではない（seed と操作の列から決まる）。記録のコインは確認値で、再実行の値と違えば diverged。同じ結果を入力と期待の両方として扱わない",
        "cross_version": "seed だけで版をまたぐ再現を保証しない。版・規約集合が違う比べは compare_runs で、結果は差の報告",
    },

    # ------------------------------------------------------------ 版
    "versions": [
        {"key": "engine_version", "status": "existing", "owner": "kyuura_engine.__version__", "changes_when": "エンジンの版ごと（処理の実装）",
         "note": "同じ版の番号に複数のコミットがある。実装の識別には足りない（D-IMPLEMENTATION-ID）"},
        {"key": "convention set version", "status": "existing", "owner": "conventions.ConventionSetIdentity（集合 ID@版・照合値）", "changes_when": "集合の中身の意味が変わるとき",
         "note": "同じ ID・版の中身は変えない（固定した照合値で確かめる）"},
        {"key": "format_version", "status": "existing", "owner": "serialize.FORMAT_VERSIONS（1〜35）", "changes_when": "書き出しの形が変わるとき（値の語彙を足すだけなら変えない）",
         "note": "一方向の書き出し。スナップショットの形式と別の番号にする"},
        {"key": "record_format", "status": "existing", "owner": "tools/engine_lockstep.py（1・2）", "changes_when": "道具の記録の形が変わるとき",
         "note": "検証用の道具の形式。再現用記録の形式として読み替えない"},
        {"key": "kyuura_diagnostic_schema", "status": "proposed", "owner": "診断の型（U1）", "changes_when": "診断の項目の形・分類の語彙が変わるとき", "note": "1 から"},
        {"key": "kyuura_replay_format", "status": "proposed", "owner": "完全な再現用記録（U3）", "changes_when": "記録の形が変わるとき", "note": "1 から"},
        {"key": "kyuura_view_format", "status": "proposed", "owner": "閲覧用記録（U5）", "changes_when": "閲覧用記録の形が変わるとき", "note": "1 から（診断の版と合わせるかは D-VERSIONS）"},
        {"key": "kyuura_snapshot_format", "status": "proposed", "owner": "状態スナップショット（U6）", "changes_when": "スナップショットの形が変わるとき", "note": "1 から"},
    ],
    "compatibility_rules": [
        "知らない形式の版・知らない項目・知らない値（決定の種類・再開先・イベントの種類・持続する効果の種類）は拒否する（compatibility）。形式の番号が同じでも、前の版の読む側が後の版の書き出しを読めるとは約束しない（serialize の互換性の約束と同じ）",
        "知らない決定（この版が知らない再開先・前の版の決定）を待つ状態は、UNSUPPORTED_DECISION で拒否する（v0.140 の入口をそのまま使う）",
        "対応しない規約集合（登録と内容が違う・知らない ID・版）は UNSUPPORTED_CONVENTION_SET で拒否する",
        "古い記録・形式 35 の書き出し・lockstep の記録を、スナップショットや再現用記録として黙って読み替えない（項目の名前が別なので、形で区別できる）",
        "旧記録の自動移行と、すべての過去の版への対応は前提にしない（必要なら移行の道具を別に作り、移行したことを記録に書く）",
        "実装の識別が違う記録の再現は unsupported を返す（seed が同じでも）。比べたいときは compare_runs",
    ],

    # ------------------------------------------------------------ 例（未実装の API の形の例示）
    "examples": [
        {"id": "EX1-ACCEPTED", "title": "通常の操作の成功", "api_status": "illustrative",
         "situation": "番のプレイヤー 0 が手札の基本エネルギーカードをバトル場のポケモンにつける",
         "payload": {"kyuura_diagnostic_schema": 1, "outcome": "accepted", "category": None, "diagnostic_id": None, "case_id": None, "case_status": None,
                     "stage": "turn_action", "status": "in_progress", "continuable": True, "next": [{"kind": "turn_action", "player": 0}],
                     "ref": {"game_id": "g-0001", "segment": 0, "step": 12, "decision_id": None},
                     "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"}},
         "views": {"actor": {"outcome": "accepted", "status": "in_progress"}, "opponent": {"events": ["attach_energy"]}, "spectator": {"events": ["attach_energy"]}}},
        {"id": "EX2-ILLEGAL", "title": "不正な操作による拒否", "api_status": "illustrative",
         "situation": "番でないプレイヤー 1 が番の終わりを送る",
         "payload": {"kyuura_diagnostic_schema": 1, "outcome": "rejected", "category": "invalid_input", "subkind": "command", "diagnostic_id": "NOT_YOUR_TURN",
                     "case_id": None, "case_status": "not_applicable", "stage": "turn_action", "status": "in_progress",
                     "continuable": True, "next": [{"kind": "turn_action", "player": 0}], "message": "今はあなたの番ではありません。",
                     "ref": {"game_id": "g-0001", "segment": 0, "step": 13, "decision_id": None},
                     "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"}},
         "views": {"actor": {"outcome": "rejected", "category": "invalid_input", "diagnostic_id": "NOT_YOUR_TURN"}, "opponent": None, "spectator": None}},
        {"id": "EX3-UNRESOLVED", "title": "未裁定での停止（宣言の拒否）", "api_status": "illustrative",
         "situation": "はらだいこを宣言したが、配分を読まない下限が 2 より小さく、山札に基本エネルギーカードがあるかもしれない（v0.151 の保守的な停止）",
         "payload": {"kyuura_diagnostic_schema": 1, "outcome": "rejected", "category": "unresolved_ruling", "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT",
                     "case_id": None, "case_status": "not_identified", "stage": "turn_action",
                     "status": "in_progress", "continuable": True, "next": [{"kind": "turn_action", "player": 0}],
                     "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンはこの操作を受け付けません。",
                     "ref": {"game_id": "g-0002", "segment": 0, "step": 40, "decision_id": None},
                     "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"}},
         "views": {"actor": {"outcome": "rejected", "category": "unresolved_ruling", "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT",
                             "case_status": "not_identified"}, "opponent": None, "spectator": None}},
        {"id": "EX4-LIMIT", "title": "技術的上限による非対応", "api_status": "illustrative",
         "situation": "相手のうらのカード（マチスの秘策）を 2 枚以上指定する操作で、受け付けるかを本当のカードによらず確かめる回数の上限を超える",
         "payload": {"kyuura_diagnostic_schema": 1, "outcome": "rejected", "category": "technical_limit", "diagnostic_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES",
                     "case_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES", "case_status": "identified", "stage": "turn_action", "status": "in_progress",
                     "continuable": True, "next": [{"kind": "turn_action", "player": 0}], "ref": {"game_id": "g-0003", "segment": 0, "step": 21, "decision_id": None},
                     "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"}},
         "views": {"actor": {"outcome": "rejected", "category": "technical_limit", "diagnostic_id": "UNSUPPORTED_SECRET_PLAN_IDENTITIES"}, "opponent": None, "spectator": None}},
        {"id": "EX5-DEV-VS-SAFE", "title": "秘密情報を含む開発用診断と、安全な閲覧者向け診断", "api_status": "illustrative",
         "situation": "EX3 と同じ拒否。検証者の詳細には実際の山札の枚数・解決の記録が入りうるが、本人には決まった文、相手・観戦者には何も送らない",
         "payload": {"verifier": {"mapped": True, "engine_code": "UNRESOLVED_STATED_CARDS_SHORT", "exception_type": "UnsupportedError",
                                  "raw_message": "<例外の生の文>", "traceback": "<traceback>", "command": {"type": "use_attack", "player": 0, "attack": 0},
                                  "developer_detail": {"trace": "<apply_command_traced の解決の記録（v0.152 では作らない）>",
                                                       "secret_note": "実際の山札の基本エネルギーカード 3 枚・うらのサイド 4 枚（例示）"}}},
         "views": {"actor": {"outcome": "rejected", "category": "unresolved_ruling", "diagnostic_id": "UNRESOLVED_STATED_CARDS_SHORT", "message": "<コードに対応する定型文>"},
                   "opponent": None, "spectator": None}},
        {"id": "EX6-DECISION-RECORD", "title": "決定待ちを含む再現用記録", "api_status": "illustrative",
         "situation": "パソコン通信で山札をさがす決定が出て、次の歩で答える（記録は検証者だけ）",
         "payload": {"kyuura_replay_format": 1,
                     "header": {"engine": {"version": "0.151.0", "implementation_digest": "<sha256>"}, "runtime": {"python": "CPython 3.14.6"},
                                "dependencies": {"rules": "<RuleSet.id>", "card_data": {"commit": "<kyuura の commit>", "digest": "<sha256>"}, "effects": "<登録表の id>"},
                                "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"},
                                "initial": {"decklists": ["<60 枚>", "<60 枚>"], "seed": 7, "rng": "python-random-mt19937-v3"}, "game_id": "g-0004"},
                     "steps": [
                         {"index": 30, "segment": 0, "actor": 0, "command": {"type": "play_trainer", "player": 0, "card": 17},
                          "outcome": {"result": "accepted"}, "check": {"state_digest": "<sha256>", "log_length": 211, "status": "awaiting_decision",
                                                                        "decision": {"id": 9, "kind": "search_deck"}}},
                         {"index": 31, "segment": 0, "actor": 0, "decision_id": 9, "command": {"type": "resolve_decision", "player": 0, "decision": 9, "choices": [42]},
                          "outcome": {"result": "accepted"}, "check": {"state_digest": "<sha256>", "log_length": 215, "status": "in_progress", "decision": None}}],
                     "footer": None},
         "views": {"opponent": {"decision": {"id": 9, "kind": "search_deck", "player": 0, "options": None}}}},
        {"id": "EX7-SUDDEN-DEATH", "title": "サドン・デスの区間を含む記録", "api_status": "illustrative",
         "situation": "同時のきぜつでサドン・デスに移り、StartSuddenDeath で延長戦（サイド 1 枚）を始め、延長戦で勝ちが決まる",
         "payload": {"kyuura_replay_format": 1,
                     "steps": [{"index": 88, "segment": 0, "actor": 1, "command": {"type": "use_attack", "player": 1, "attack": 0},
                                "outcome": {"result": "accepted"}, "check": {"status": "sudden_death_pending"}},
                               {"index": 89, "segment": 0, "actor": 0, "command": {"type": "start_sudden_death", "player": 0},
                                "outcome": {"result": "accepted"}, "check": {"status": "in_progress", "segment": 1}}],
                     "segments": [{"index": 0, "start_step": 0, "prize_count": 0, "result": {"outcome": "sudden_death"}},
                                  {"index": 1, "start_step": 89, "prize_count": 1, "result": {"outcome": "win", "winner": 0}}],
                     "footer": {"reason": "game_over", "steps": 140, "final_state_digest": "<sha256>"}},
         "views": {"spectator": {"segment": {"index": 1, "prize_count": 1, "previous": [{"index": 0, "outcome": "sudden_death"}]}}}},
        {"id": "EX8-REPLAY-REFUSED", "title": "非対応の版・規約による再現の拒否", "api_status": "illustrative",
         "situation": "記録の規約集合 CS-KYUURA-PLAY-S2A@1 の照合値が、この実装の登録と違う（または記録の形式の版 2 をこの実装が知らない）",
         "payload": {"replay": "unsupported", "reasons": [{"item": "convention_set.digest", "recorded": "<記録の照合値>", "expected": "<登録の照合値>"},
                                                         {"item": "kyuura_replay_format", "recorded": 2, "supported": [1]}],
                     "category": "compatibility", "diagnostic_id": "UNSUPPORTED_CONVENTION_SET"},
         "views": {}},
        {"id": "EX9-HALTED", "title": "操作の結果として停止した状態", "api_status": "illustrative",
         "situation": "番の終わりを受け付け、ポケモンチェックで未裁定の場面に当たって HALTED になる（拒否ではない）",
         "payload": {"kyuura_diagnostic_schema": 1, "outcome": "accepted", "category": None, "diagnostic_id": None, "status": "halted",
                     "halt": {"category": "unresolved_ruling", "diagnostic_id": "UNRESOLVED_SCRAM_TIMING", "case_id": None, "case_status": "not_identified",
                              "message": "この場面の扱いは、基準のルールと記録からは決まらないため、エンジンは対戦を止めました。", "interrupted": False},
                     "case_status": None, "stage": "turn_action", "continuable": False, "next": [],
                     "ref": {"game_id": "g-0005", "segment": 0, "step": 77, "decision_id": None},
                     "convention_set": {"id": "CS-KYUURA-CURRENT", "version": 1, "digest": "<照合値>"}},
         "views": {"actor": {"status": "halted", "halt": {"diagnostic_id": "UNRESOLVED_SCRAM_TIMING"}},
                   "opponent": {"status": "halted", "halt": {"diagnostic_id": "UNRESOLVED_SCRAM_TIMING"}},
                   "spectator": {"status": "halted", "halt": {"diagnostic_id": "UNRESOLVED_SCRAM_TIMING"}}}},
    ],

    # ------------------------------------------------------------ 利用者の判断事項（どれも pending）
    "decisions": [
        {"id": "D-MESSAGE", "question": "本人に返す拒否の理由の文を、エンジンの生の文にするか、コードごとの決まった文にするか",
         "options": ["生の文（今の apply_command の呼び出し元が受け取る文と同じ）", "コードごとの決まった文の表（文の秘密の検査がいらない）"],
         "recommendation": "最初は生の文を本人と検証者だけに返し、プログラムでは code で判定する。v0.135〜v0.151 の対象群の外で文が配分によるかは未確認なので、双子の比較の対象を広げるまで、オンラインの相手には送らない",
         "status": "adopted", "adopted": "本人向けは、原則としてコードに対応する安全な定型文。生の例外文と内部の詳細は検証者用（推奨案ではなく、決まった文の表を採用）",
         "adoption": "ADOPT-U1-U2"},
        {"id": "D-REJECTED", "question": "完全な再現用記録に、拒否された操作を記録するか",
         "options": ["すべて記録する（確認値として。再現の入力ではない）", "記録しない（受理した操作だけ）"],
         "recommendation": "すべて記録する。拒否の結果（コード・文の指紋）は情報漏れの調査に要る。再現は受理した操作だけで行い、拒否の歩は同じ拒否になるかを確かめる", "status": "adopted",
         "adopted": "将来の完全記録へ任意で残せる設計にする（受理した操作の再現とは区別する）。v0.152 は操作との対応（operation_id・結果・検証者用の記録）の境界だけで、記録はしない",
         "adoption": "ADOPT-U1-U2"},
        {"id": "D-CHECK-DENSITY", "question": "確認値（状態の指紋）を毎歩書くか、間引くか",
         "options": ["毎歩（lockstep と同じ）", "決定・区間の境界・終わりだけ"], "recommendation": "毎歩。最初に違った歩を返すのに要る。大きさが問題になったら間引く選択肢を形式の版で加える",
         "status": "pending"},
        {"id": "D-IMPLEMENTATION-ID", "question": "実装の識別を何で表すか",
         "options": ["パッケージのソースと同梱データの内容の sha256（implementation_digest）", "git のコミットと変更の有無", "エンジンの版の番号だけ"],
         "recommendation": "内容の sha256 を必須にし、分かれば git のコミットを参考に書く。版の番号だけでは同じ版の別のコミットを区別できない", "status": "pending"},
        {"id": "D-RUNTIME", "question": "Python の版が違う環境での再現を、保証の範囲に入れるか",
         "options": ["同じ版だけ（違えば unsupported）", "記録するが拒否しない（結果に環境の違いを書く）"],
         "recommendation": "記録し、違えば結果に環境の違いを書いて再実行する（拒否しない）。保証は同じ実装・同じ依存までにする（api-review の Python 3.11〜3.13 の確認は過去の確認）",
         "status": "pending"},
        {"id": "D-POSTGAME", "question": "対戦が終わったあと、閲覧用記録で相手のデッキリスト・seed などを公開するか",
         "options": ["公開しない（対戦中と同じ）", "対戦の終わりに公開する（別の承認の記録が要る）"], "recommendation": "公開しない。公開するなら閲覧用記録の版と、公開の時点を決める",
         "status": "adopted", "adopted": "対戦後も情報の公開範囲を自動では広げない", "adoption": "ADOPT-U1-U2"},
        {"id": "D-VERSIONS", "question": "新しい 4 つの版（診断・再現用記録・閲覧用記録・スナップショット）を分けるか",
         "options": ["4 つに分ける", "診断と閲覧用記録を 1 つにまとめ、3 つにする"],
         "recommendation": "4 つに分ける。どれも整数 1 つで、形が変わったときだけ上げる。値の語彙を足すだけでは上げない（serialize の約束と同じ）", "status": "pending"},
        {"id": "D-SNAPSHOT-BASE", "question": "スナップショットを形式 35 の書き出しに乱数の状態を足したものにするか、別の形にするか",
         "options": ["形式 35 + 乱数（形式 35 が落とさず表すことを U6 で確かめたうえで）", "新しい形（状態の項目から直接）"],
         "recommendation": "U6 の最初に、形式 35 から状態をもどせるかの監査をしてから決める。監査の前に形式 35 を読み込みの形式として約束しない", "status": "pending"},
        {"id": "D-HALT-SNAPSHOT", "question": "HALTED の状態のスナップショットを作れるようにするか",
         "options": ["作れる（再開はしない。調査・表示用）", "作らない"], "recommendation": "作れる。ただし再開の API はなく、続行規約の採用で再開することは別の判断", "status": "pending"},
        {"id": "D-STATE-INTEGRITY-VIEW", "question": "状態の不整合（state_integrity）を、プレイヤーに内部エラーと同じ見え方で返すか",
         "options": ["同じ（対戦を止める。内容は検証者だけ）", "別の表示（壊れた保存の可能性を伝える）"], "recommendation": "対戦を止めることは同じにし、分類の名前は分けて返す", "status": "adopted",
         "adopted": "本人にも一般的な説明だけを返す（内部の値・カードの識別を出さない）。分類は state_integrity のまま（内部エラー・未対応に変えない）", "adoption": "ADOPT-U1-U2"},
    ],

    # ------------------------------------------------------------ 実装単位
    "units": [
        {"id": "U1", "title": "診断の共通データ型と情報境界", "depends": [], "status": "implemented",
         "scope": ["kyuura_engine の新しいモジュール（診断の型・分類・見る人ごとの写し）", "台帳から作る同梱のコード表（停止コード → 分類・事例。台帳の生成元から作り、手で書かない）"],
         "reuse": ["EX-ERRORS", "EX-STOP-LEDGER", "EX-HALT"],
         "tests": ["台帳のすべての停止コード（scan の engine_prefixed_codes）が分類に入り、unlisted が 0", "内部エラー（EngineError でない例外）が internal_error 以外にならない",
                   "見る人ごとの写しに、検証者だけの項目（developer_detail・seed・乱数・状態の指紋）が入らない",
                   "v0.147〜v0.151 の双子で、本人・相手・観戦者の診断の写しが同じ（twin_command_problems を写しに当てる）"],
         "done": ["分類の規則が仕様の classification_rules と同じ", "エンジンの動作・既存の公開 API を変えていない", "既存の双子のテストが通る"]},
        {"id": "U2", "title": "コマンド実行結果のアダプタ", "depends": ["U1"], "status": "implemented",
         "scope": ["apply_command を包む関数（状態・コマンド・操作するプレイヤー → 結果と診断）", "new_game の前の入力の確かめ（seed の型・範囲を invalid_input にする）"],
         "reuse": ["EX-APPLY-COMMAND", "EX-RESUME-GUARD", "EX-CONVENTION-ID"],
         "tests": ["rejected で状態・乱数・ログが変わらない（command_outcome と同じ確かめ）", "受理・拒否・失敗の 3 つと status の 5 つの組み合わせ",
                   "決定待ち・HALTED・サドン・デスの status と next", "古い状態への操作を、アダプタが持つ今の状態と違えば受け付けない（P-NO-FREE-REDO）"],
         "done": ["apply_command の結果と、アダプタの受理・拒否が一致（同じ入力で）", "例外を広く捕まえない（EngineError だけを診断にし、ほかは internal_error として記録して投げ直す）"]},
        {"id": "U3", "status": "planned", "title": "完全な再現用記録の収集と検証", "depends": ["U2"],
         "scope": ["アダプタの結果から記録を作る収集器", "記録の形・見出し・歩の番号・終わりの印の検証"],
         "reuse": ["EX-LOCKSTEP", "EX-COMMAND-CODEC", "EX-STATE-EXPORT", "EX-CONVENTION-ID", "EX-SUDDEN-DEATH"],
         "tests": ["見出しの必須の項目が欠けた記録・番号の飛んだ記録・終わりの印のない記録の区別", "サドン・デスの区間の境界", "拒否の歩を記録しても再現の入力に入らない"],
         "done": ["記録が lockstep の記録と別の形式（kyuura_replay_format）で、どちらも黙って読み替えない"]},
        {"id": "U4", "status": "planned", "title": "再現インターフェース", "depends": ["U3"],
         "scope": ["replay_from_start・verify_record・compare_runs"],
         "reuse": ["EX-LOCKSTEP", "EX-LOG-AUDIT"],
         "tests": ["固定の少数の対戦（seed と目的を先に決める）で succeeded", "1 歩を書き換えた記録で diverged と最初の歩・項目", "実装の識別・規約集合を変えた記録で unsupported",
                   "内部エラーを diverged にしない", "方策を再実行しない（記録のコマンドだけで進む）"],
         "done": ["同じ実装・同じ依存・同じ規約集合・同じ初期の条件・同じ操作列で、各歩の確認値と同じ", "compare_runs が成功を返さない"]},
        {"id": "U5", "status": "planned", "title": "閲覧用記録", "depends": ["U1", "U3"],
         "scope": ["完全な記録（または進行中の状態）から見る人ごとの記録を作る"],
         "reuse": ["EX-OBSERVE", "EX-DECISION", "EX-SUDDEN-DEATH"],
         "tests": ["閲覧用記録が対戦中の観測・ログの写しと同じ", "seed・乱数・状態の指紋・相手のコマンド・相手の拒否が入らない", "双子の完全な記録から作った相手・観戦者の閲覧用記録が同じ"],
         "done": ["閲覧用記録から完全な記録を作る関数を作らない"]},
        {"id": "U6", "status": "planned", "title": "JSON の保存・復元への接続", "depends": ["U3", "U4"],
         "scope": ["形式 35 から状態をもどせるかの監査（D-SNAPSHOT-BASE の材料）", "スナップショットの書き出し・読み込み・確かめ"],
         "reuse": ["EX-RNG-JSON", "EX-RESUME-GUARD", "EX-CONVENTION-ID", "EX-STATE-EXPORT"],
         "tests": ["保存して復元し、続きを送った結果が保存しなかった場合と同じ（固定の少数の対戦・決定待ち・区間の途中）", "知らない形式・項目・再開先・規約集合の拒否",
                   "壊したスナップショットが StateIntegrityError か invalid_record になる"],
         "done": ["pickle を保存の形式にしない", "形式 35 の意味を変えない"]},
        {"id": "U7", "status": "planned", "title": "合法手 API・GUI アダプタへの接続", "depends": ["U2", "U5"],
         "scope": ["合法手の一覧の境界（見る人の知る情報だけで作る。秘密の配分で候補が変わらない）", "GUI・AI・オンライン対戦が使う境界の文書（実装は採用の判断のあと）"],
         "reuse": ["EX-OBSERVE", "EX-DECISION", "EX-TWIN-AUDIT"],
         "tests": ["双子で合法手の一覧が同じ", "一覧の手がアダプタで rejected にならない（または理由が分類で説明できる）"],
         "done": ["オンライン対戦・本格的な画面を作らない（境界だけ）"]},
    ],
}


# ------------------------------------------------------------ 生成


def build() -> dict:
    return copy.deepcopy(SPEC)


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    if isinstance(value, (list, tuple)):
        return "<br>".join(_cell(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers, rows) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return lines


def _refs(refs) -> str:
    return "<br>".join(f"`{r}`" for r in refs)


def blocks(spec: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    out["existing"] = _table(["ID", "もの", "状態", "参照", "今あるもの", "再利用", "限界"],
                             [[e["id"], e["name"], e["status"], _refs(e["refs"]), e["provides"], e["reuse"], e["limits"]] for e in spec["existing"]])
    out["categories"] = _table(["分類", "意味", "発生元", "区分", "状態への影響", "続けられる"],
                               [[f"`{c['id']}`", c["label"], c["sources"], ", ".join(c["subkinds"]), c["state_effect"], c["continuable"]] for c in spec["categories"]])
    out["classification-rules"] = (_table(["順", "条件", "分類", "根拠"], [[r["order"], r["when"], f"`{r['category']}`", r["basis"]] for r in spec["classification_rules"]])
                                   + ["", "互換性の表（compatibility_codes）: " + "、".join(f"`{c}`" for c in spec["compatibility_codes"])])
    out["outcomes"] = (_table(["結果", "意味", "状態", "分類", "次"], [[f"`{o['id']}`", o["meaning"], o["state"], ", ".join(o["categories"]), o["next"]] for o in spec["outcomes"]])
                       + [""] + _table(["status", "意味"], [[f"`{s['id']}`", s["meaning"]] for s in spec["statuses"]])
                       + [""] + _table(["stage", "意味"], [[f"`{s['id']}`", s["meaning"]] for s in spec["stages"]]))
    out["diagnostic-fields"] = _table(["項目", "固定か説明用か", "必須", "渡す相手", "意味"],
                                      [[f"`{f['field']}`", f["stability"], f["required"], f["audience"], f["meaning"]] for f in spec["diagnostic_fields"]])
    out["roles"] = _table(["権限", "意味", "持つもの"], [[f"`{r['id']}`", r["meaning"], r["holder"]] for r in spec["roles"]])
    out["visibility"] = _table(["項目", "群", "本人", "相手", "観戦者", "検証者", "根拠"],
                               [[v["item"], v["group"], v["actor"], v["opponent"], v["spectator"], v["verifier"], v["basis"]] for v in spec["visibility"]])
    out["principles"] = _table(["ID", "約束", "由来", "確かめ"], [[p["id"], p["rule"], p["origin"], p["check"]] for p in spec["principles"]])
    lines: list[str] = []
    for r in spec["records"]:
        lines += [f"#### {r['label']}（`{r['version_key']}`）", "",
                  f"- 用途: {r['purpose']}", f"- 持つ側: {r['holder']}", f"- 秘密の情報を含む: {_cell(r['contains_secrets'])}",
                  f"- 再現の入力: {'、'.join(r['inputs']) or 'なし'}", f"- 確認値: {'、'.join(r['expected']) or 'なし'}",
                  f"- 保証: {'。'.join(r['guarantees'])}", f"- 保証しない: {'。'.join(r['not_guaranteed'])}", ""]
        lines += _table(["項目", "必須", "役割", "意味"], [[f"`{f['name']}`", f["required"], f["role"], f["meaning"]] for f in r["fields"]]) + [""]
    lines += ["共通の部分: " + "、".join(spec["record_common"])]
    out["records"] = lines
    g = spec["guarantee_scope"]
    out["replay"] = (_table(["関数", "意味", "使う記録", "返しうる結果"],
                            [[f"`{f['id']}`", f["meaning"], ", ".join(f["uses"]), ", ".join(f["results"])] for f in spec["replay_functions"]])
                     + [""] + _table(["結果", "意味"], [[f"`{r['id']}`", r["meaning"]] for r in spec["replay_results"]])
                     + ["", "保証の範囲（すべて同じとき）: " + "、".join(g["same"]), "", f"- 乱数: {g['rng']}", f"- コイン: {g['coins']}", f"- 版をまたぐ比べ: {g['cross_version']}"])
    out["versions"] = (_table(["版の項目", "状態", "持ち主", "変わるとき", "注"], [[f"`{v['key']}`", v["status"], v["owner"], v["changes_when"], v["note"]] for v in spec["versions"]])
                       + [""] + [f"- {rule}" for rule in spec["compatibility_rules"]])
    lines = []
    for e in spec["examples"]:
        lines += [f"#### {e['id']}: {e['title']}（`api_status`: {e['api_status']}）", "", e["situation"], "", "```json",
                  json.dumps(e["payload"], ensure_ascii=False, indent=1), "```", ""]
        if e["views"]:
            lines += ["見る人ごとの写し（null は送らない）:", "", "```json", json.dumps(e["views"], ensure_ascii=False, indent=1), "```", ""]
    out["examples"] = lines[:-1]
    out["units"] = _table(["単位", "状態", "内容", "依存", "変更範囲", "再利用", "回帰テスト", "完了基準"],
                          [[u["id"], u["status"], u["title"], ", ".join(u["depends"]) or "なし", u["scope"], ", ".join(u["reuse"]), u["tests"], u["done"]]
                           for u in spec["units"]])
    out["decisions"] = _table(["ID", "問い", "選択肢", "推奨", "状態", "採用した内容"],
                              [[d["id"], d["question"], d["options"], d["recommendation"], d["status"], d.get("adopted", "")] for d in spec["decisions"]])
    a_lines = []
    for a in spec["adoptions"]:
        a_lines += [f"- `{a['id']}`（{a['date']}・{a['by']}）: {a['scope']}。実装: {a['implemented_in']}", "  - 方針:"]
        a_lines += [f"    - {p}" for p in a["policies"]]
        a_lines += [f"  - 判断事項: {'、'.join(a['decisions'])}", f"  - 実装単位: {'、'.join(a['units'])}"]
    out["adoptions"] = a_lines
    return out


DESIGN_BLOCKS = ("adoptions", "existing", "categories", "classification-rules", "outcomes", "diagnostic-fields", "roles", "visibility", "principles", "records", "replay",
                 "versions", "examples")
PLAN_BLOCKS = ("units", "decisions")
_BLOCK = re.compile(r"(<!-- generated:(?P<name>[a-z-]+) begin -->\n)(?P<body>.*?)(<!-- generated:(?P=name) end -->)", re.DOTALL)


def render_into(text: str, rendered: dict[str, list[str]], names) -> tuple[str, list[str]]:
    """文書の生成区画を置きかえた文と、区画の問題（ない・余分・重なり）。"""
    problems = []
    found = [m.group("name") for m in _BLOCK.finditer(text)]
    for name in names:
        if found.count(name) != 1:
            problems.append(f"生成区画 {name} が {found.count(name)} 個（1 個であること）")
    for name in found:
        if name not in names:
            problems.append(f"知らない生成区画 {name}")
    text = _BLOCK.sub(lambda m: m.group(1) + "\n".join(rendered[m.group("name")]) + "\n" + m.group(4) if m.group("name") in rendered else m.group(0), text)
    return text, problems


# ------------------------------------------------------------ 確かめ


def _defined(path: pathlib.Path, name: str) -> bool:
    text = path.read_text(encoding="utf-8")
    pattern = rf"^\s*(?:def|class)\s+{re.escape(name)}\b|^{re.escape(name)}\s*(?::[^=\n]*)?="
    return re.search(pattern, text, re.MULTILINE) is not None


def ref_problems(ref: str) -> list[str]:
    path, _, symbol = ref.partition("::")
    target = ROOT / path
    if not target.exists():
        return [f"参照 {ref}: ファイル {path} がない"]
    if symbol and not _defined(target, symbol):
        return [f"参照 {ref}: {path} に {symbol} の定義がない"]
    return []


def known_codes() -> tuple[set[str], set[str], dict[str, dict]]:
    """エンジンのソースの文字列のコードと、台帳の項目（ID → 項目）、事例 ID の集合。"""
    literals: set[str] = set()
    for p in (ROOT / "kyuura_engine").rglob("*.py"):
        literals |= set(re.findall(r'"([A-Z][A-Z0-9_]{2,})"', p.read_text(encoding="utf-8")))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = {e["id"]: e for e in ledger["entries"]}
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    cases = {i for i in entries if "#" in i} | {scene["id"] for scene in records["scene_index"]["scenes"]}
    return literals, cases, entries


def _walk(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield f"{path}.{k}" if path else k, k, v
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def spec_problems(spec: dict) -> list[str]:
    """JSON に書いた仕様の中身の矛盾（文書との一致は ``check`` が別に見る）。"""
    problems: list[str] = []
    if spec.get("approval") != "not_approved" or spec.get("status") != "proposed":
        problems.append("仕様案が承認済みになっている（approval は not_approved、status は proposed のまま。採用は adoptions に範囲を限って書く）")
    adoptions = {a["id"]: a for a in spec.get("adoptions", [])}
    adopted_decisions = {d for a in adoptions.values() for d in a["decisions"]}
    adopted_units = {u for a in adoptions.values() for u in a["units"]}
    for d in spec["decisions"]:
        if d.get("status") == "adopted":
            if d.get("adoption") not in adoptions or d["id"] not in adoptions[d["adoption"]]["decisions"] or not d.get("adopted"):
                problems.append(f"判断事項 {d['id']} が、採用の記録（adoptions）にないのに adopted になっている")
        elif d.get("status") != "pending":
            problems.append(f"判断事項 {d['id']} が pending・adopted でない")
    for d in adopted_decisions - {d["id"] for d in spec["decisions"] if d.get("status") == "adopted"}:
        problems.append(f"採用の記録の判断事項 {d} が adopted になっていない")
    for u in spec["units"]:
        if u.get("status") not in ("implemented", "planned"):
            problems.append(f"実装単位 {u['id']} の状態 {u.get('status')} が語彙にない")
        if (u.get("status") == "implemented") != (u["id"] in adopted_units):
            problems.append(f"実装単位 {u['id']} の状態が、採用の記録の単位と合わない")
    for e in spec["examples"]:
        if e.get("api_status") != "illustrative":
            problems.append(f"例 {e['id']} が例示（illustrative）になっていない（実際の出力の例は版の文書に書く）")

    # 参照
    for e in spec["existing"]:
        if e["status"] not in FEATURE_STATUS:
            problems.append(f"既存の機能 {e['id']} の状態 {e['status']} が語彙にない")
        if e["status"] != "not_implemented" and not e["refs"]:
            problems.append(f"既存の機能 {e['id']} に参照がない")
        for ref in e["refs"]:
            problems += ref_problems(ref)
    for key in ("design", "plan", "generator", "test"):
        problems += ref_problems(spec["documents"][key])
    for key in ("stop_ledger", "scene_index"):
        problems += ref_problems(spec["sources"][key])

    # 分類
    category_ids = [c["id"] for c in spec["categories"]]
    if tuple(category_ids) != CATEGORIES:
        problems.append(f"分類の並び {category_ids} が {CATEGORIES} と違う")
    rules = spec["classification_rules"]
    if [r["order"] for r in rules] != list(range(1, len(rules) + 1)):
        problems.append("分類の規則の順が 1 から連続していない")
    for r in rules:
        if r["category"] not in CATEGORIES:
            problems.append(f"分類の規則 {r['order']} の分類 {r['category']} が分類にない")
    if not rules or rules[0]["category"] != "internal_error" or "EngineError でない" not in rules[0]["when"]:
        problems.append("最初の規則が「EngineError でない例外 → internal_error」でない（内部エラーをほかの分類に変換しうる）")
    if any(r["category"] == "internal_error" for r in rules[1:]):
        problems.append("内部エラーの分類が 2 つ以上の規則に出る")
    for c in spec["categories"]:
        if c["id"] in ("internal_error", "state_integrity", "compatibility") and c["continuable"]:
            problems.append(f"分類 {c['id']} が続けられることになっている")
    outcome_ids = tuple(o["id"] for o in spec["outcomes"])
    if outcome_ids != OUTCOMES:
        problems.append(f"結果の並び {outcome_ids} が {OUTCOMES} と違う")
    seen: dict[str, str] = {}
    for o in spec["outcomes"]:
        for c in o["categories"]:
            if c not in CATEGORIES:
                problems.append(f"結果 {o['id']} の分類 {c} が分類にない")
            if c in seen:
                problems.append(f"分類 {c} が結果 {seen[c]} と {o['id']} の両方にある")
            seen[c] = o["id"]
    failed = next((o for o in spec["outcomes"] if o["id"] == "failed"), {"categories": []})
    if "internal_error" not in failed["categories"]:
        problems.append("内部エラーが failed の結果になっていない")
    missing = set(CATEGORIES) - set(seen)
    if missing:
        problems.append(f"どの結果にも入らない分類 {sorted(missing)}")
    if tuple(s["id"] for s in spec["statuses"]) != STATUSES:
        problems.append("status の並びが語彙と違う")

    # コードと事例
    literals, cases, entries = known_codes()
    for code in spec["compatibility_codes"] + spec["unresolved_generic_codes"]:
        if code not in entries:
            problems.append(f"コード {code} が台帳にない")
    for code in spec["compatibility_codes"]:
        if not code.startswith("UNSUPPORTED_"):
            problems.append(f"互換性の表のコード {code} が UnsupportedError のコードでない")
    stage_ids = {s["id"] for s in spec["stages"]}
    status_ids = set(STATUSES)
    for e in spec["examples"]:
        for path, key, value in _walk(e["payload"]):
            if key in ("code", "diagnostic_id", "engine_code") and value is not None and value not in literals and value not in entries and value not in ADAPTER_IDS:
                problems.append(f"例 {e['id']} の {path}: コード {value} がエンジン・台帳・アダプタの識別にない")
            if key == "case_id" and value is not None and value not in cases:
                problems.append(f"例 {e['id']} の {path}: 事例 {value} が台帳・場面の索引にない")
            if key == "category" and value is not None and value not in CATEGORIES:
                problems.append(f"例 {e['id']} の {path}: 分類 {value} が分類にない")
            if key == "stage" and value is not None and value not in stage_ids:
                problems.append(f"例 {e['id']} の {path}: 処理段階 {value} が語彙にない")
            if key == "status" and isinstance(value, str) and value not in status_ids:
                problems.append(f"例 {e['id']} の {path}: status {value} が語彙にない")
            if key == "outcome" and isinstance(value, str) and value not in OUTCOMES and value not in ("sudden_death", "win"):
                problems.append(f"例 {e['id']} の {path}: 結果 {value} が語彙にない")
        p = e["payload"]
        if p.get("outcome") == "rejected" and p.get("category") not in next(o["categories"] for o in spec["outcomes"] if o["id"] == "rejected"):
            problems.append(f"例 {e['id']}: rejected の分類 {p.get('category')} が rejected に入らない分類")
        for role, view in e["views"].items():
            if role not in ROLES or role == "verifier":
                problems.append(f"例 {e['id']}: 見る人の写しの {role} が、本人・相手・観戦者でない")
            for path, key, _ in _walk(view or {}):
                if key in VERIFIER_ONLY_FIELDS:
                    problems.append(f"例 {e['id']} の {role} の写し {path}: 検証者だけの項目 {key}")
                if role != "actor" and key == "message":
                    problems.append(f"例 {e['id']} の {role} の写し {path}: 本人でない人に理由の文")
        if p.get("outcome") == "rejected" and any(e["views"].get(r) is not None for r in ("opponent", "spectator")):
            problems.append(f"例 {e['id']}: 拒否が相手・観戦者に送られている")

    # 情報境界
    for v in spec["visibility"]:
        for role in ROLES:
            if v.get(role) not in VISIBILITY:
                problems.append(f"見える範囲 {v['item']}: {role} の値 {v.get(role)} が語彙にない")
        if v["verifier"] != "yes":
            problems.append(f"見える範囲 {v['item']}: 検証者に見えない（検証者は完全な情報を扱う）")
        if v["spectator"] in ("own", "decider"):
            problems.append(f"見える範囲 {v['item']}: 観戦者に own・decider は使えない")
    for marker in ("developer_detail", "seed", "乱数", "完全な状態", "halt.message", "初期の山札", "decision.resume"):
        rows = [v for v in spec["visibility"] if marker in v["item"]]
        if not rows:
            problems.append(f"見える範囲の表に {marker} の行がない")
        for v in rows:
            if any(v[r] != "no" for r in ("actor", "opponent", "spectator")):
                problems.append(f"見える範囲 {v['item']}: 検証者だけの項目が、本人・相手・観戦者に見える")
    for v in spec["visibility"]:
        if v["group"] == "diagnostic" and "拒否" in v["item"] and (v["opponent"] != "no" or v["spectator"] != "no"):
            problems.append(f"見える範囲 {v['item']}: 拒否が相手・観戦者に見える")
    if "verifier" in {r["id"] for r in spec["roles"]} and not any(p["id"] == "P-NO-PROMOTION" for p in spec["principles"]):
        problems.append("検証者の権限があるのに、引数で権限が上がらない約束（P-NO-PROMOTION）がない")

    # 記録
    record_ids = [r["id"] for r in spec["records"]]
    if record_ids != ["replay_full", "view", "snapshot"]:
        problems.append(f"記録の種類 {record_ids} が A・B・C の 3 つでない")
    version_keys = {v["key"] for v in spec["versions"]}
    for r in spec["records"]:
        if r["version_key"] not in NEW_VERSION_KEYS or r["version_key"] not in version_keys:
            problems.append(f"記録 {r['id']} の版の項目 {r['version_key']} が新しい版の表にない")
        names = [f["name"] for f in r["fields"]]
        if names[0] != r["version_key"]:
            problems.append(f"記録 {r['id']} の最初の項目が版の項目でない")
        if len(set(names)) != len(names):
            problems.append(f"記録 {r['id']} の項目が重なる")
        if r["id"] == "view":
            for f in r["fields"]:
                if any(word in f["name"] for word in ("seed", "rng", "digest", "command")):
                    problems.append(f"閲覧用記録の項目 {f['name']} が、検証者だけの値を持つ")
            if r["contains_secrets"]:
                problems.append("閲覧用記録が秘密の情報を含むことになっている")
        for f in r["fields"]:
            if f["role"] not in ("format", "input", "expected", "environment", "reference"):
                problems.append(f"記録 {r['id']} の項目 {f['name']} の役割 {f['role']} が語彙にない")
            if "coin" in f["name"] and f["role"] == "input":
                problems.append(f"記録 {r['id']} の項目 {f['name']}: コインの結果を入力にしている（確認値にする）")
            if "policy" in f["name"] and f["role"] == "input":
                problems.append(f"記録 {r['id']} の項目 {f['name']}: 方策を再現の入力にしている")
    for key in NEW_VERSION_KEYS:
        if key in EXISTING_VERSION_KEYS:
            problems.append(f"新しい版の項目 {key} が既存の項目の名前と同じ")
    for v in spec["versions"]:
        if v["status"] == "proposed" and v["key"] not in NEW_VERSION_KEYS:
            problems.append(f"提案の版の項目 {v['key']} が新しい版の表にない")

    # 再現
    for f in spec["replay_functions"]:
        for r in f["results"]:
            if r not in REPLAY_STATUS:
                problems.append(f"再現の関数 {f['id']} の結果 {r} が語彙にない")
        if f["id"] == "compare_runs" and "succeeded" in f["results"]:
            problems.append("compare_runs が成功を返す（版・規約集合をまたぐ比べは差の報告だけ）")
        if "internal_error" not in f["results"]:
            problems.append(f"再現の関数 {f['id']} が内部エラーを返さない（diverged に変えてしまう）")
    if tuple(r["id"] for r in spec["replay_results"]) != REPLAY_STATUS:
        problems.append("再現の結果の並びが語彙と違う")

    # 実装単位
    units = {u["id"]: u for u in spec["units"]}
    existing_ids = {e["id"] for e in spec["existing"]}
    for u in spec["units"]:
        for d in u["depends"]:
            if d not in units:
                problems.append(f"実装単位 {u['id']} の依存 {d} がない")
        for r in u["reuse"]:
            if r not in existing_ids:
                problems.append(f"実装単位 {u['id']} の再利用 {r} が既存の機能にない")
        if not u["tests"] or not u["done"]:
            problems.append(f"実装単位 {u['id']} に回帰テスト・完了基準がない")
    state: dict[str, int] = {}

    def visit(uid: str) -> bool:
        if state.get(uid) == 1:
            return False
        if state.get(uid) == 2:
            return True
        state[uid] = 1
        ok = all(visit(d) for d in units[uid]["depends"] if d in units)
        state[uid] = 2
        return ok

    if not all(visit(uid) for uid in units):
        problems.append("実装単位の依存が循環している")
    order = [u["id"] for u in spec["units"]]
    for u in spec["units"]:
        for d in u["depends"]:
            if d in order and order.index(d) > order.index(u["id"]):
                problems.append(f"実装単位 {u['id']} が、あとの単位 {d} に依存する（推奨の順と合わない）")
    decision_ids = {d["id"] for d in spec["decisions"]}
    text = json.dumps(spec, ensure_ascii=False)
    for ref in sorted(set(re.findall(r"(?<![A-Za-z0-9_-])D-[A-Z][A-Z-]+[A-Z]", text))):
        if ref not in decision_ids:
            problems.append(f"判断事項 {ref} への参照があるが、判断事項にない")
    return problems


def check(written: dict, design: str, plan: str) -> list[str]:
    spec = build()
    problems = []
    if written != spec:
        problems.append("書いた JSON が、作り直した仕様案と違う（--write で作り直す）")
    rendered = blocks(spec)
    for name, text, names in (("設計の文書", design, DESIGN_BLOCKS), ("実装計画の文書", plan, PLAN_BLOCKS)):
        new, block_problems = render_into(text, rendered, names)
        problems += [f"{name}: {p}" for p in block_problems]
        if new != text:
            problems.append(f"{name}の生成区画が、作り直したものと違う（--write で作り直す）")
    problems += spec_problems(written)
    return problems


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
        rendered = blocks(spec)
        for path, names in ((DESIGN, DESIGN_BLOCKS), (PLAN, PLAN_BLOCKS)):
            text, block_problems = render_into(path.read_text(encoding="utf-8"), rendered, names)
            if block_problems:
                print("\n".join(f"{path.name}: {p}" for p in block_problems))
                return 1
            path.write_text(text, encoding="utf-8", newline="\n")
        print("書いた")
        return 0
    if not OUTPUT.exists():
        print("仕様案の JSON がない（--write で作る）")
        return 1
    problems = check(json.loads(OUTPUT.read_text(encoding="utf-8")), DESIGN.read_text(encoding="utf-8"), PLAN.read_text(encoding="utf-8"))
    print("\n".join(problems) if problems else "problems=0")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
