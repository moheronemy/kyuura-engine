"""異常の判定（D-6。V3-1 で採用した範囲。docs/verification-ai-v3-1.md 2 章）。検証者の側だけで使い、方策・行動生成・変異の部品には渡しません。

- ``snapshot``・``compare``: 変異の要求の前後の、状態の確認値（状態の sha256・乱数の指紋・ログの長さ・決定・停止・区間・状態の区分）・状態のオブジェクトの置きかえ・閲覧者ごとの
  更新の数（取り出さずに数える）・更新の番号・処理できない結果の有無
- ``judge_negative``・``judge_recovery``: 変異の要求と、変異のあとの元の入力の check の判定
- ``judge_normal``・``judge_termination``: 通常の進行の送信と終わり方の判定（API の保証の 2 分類で読む）

``ClientHub`` には更新を取り出さずに数える公開の口がないので、検証者の側で内部の ``_outbox``・``_seq`` を読みます（取り出さない。配る順・カーソルを変えない）。
"""

from __future__ import annotations

from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine.replay_record import checks

# 判定の規則の版。1: V3-1（8091ed6）。2: V3-2（停止系の拒否を known_stop にする条件を、診断のコード表と経路の理由で絞る。docs/verification-ai-v3-2.md 5 章）
JUDGE_RULES_VERSION = 2
# 候補・選べるもの・組の理由のうち、エンジンの側の確かめを候補の作成では評価していないことを示すもの（停止・拒否がこの経路でありうると API が示している）
EXPLAINING_REASONS = frozenset({"preflight_not_evaluated", "continuation_not_evaluated", "reactions_not_evaluated", "use_condition_not_evaluated",
                                "face_down_reveal_not_evaluated", "segment_setup_not_evaluated", "turn_start_not_evaluated", "checkup_not_evaluated"})

EXPECTED = "expected"
NORMAL_REJECTION = "normal_rejection"
KNOWN_STOP = "known_stop"
KNOWN_LIMITATION = "known_limitation"
SUSPECT = "suspect"
UNDETERMINED = "undetermined"
NOT_APPLICABLE = "not_applicable"
VERDICTS = (EXPECTED, NORMAL_REJECTION, KNOWN_STOP, KNOWN_LIMITATION, SUSPECT, UNDETERMINED)
AUDIENCES = (0, 1, "spectator", "host")
STOP_CATEGORIES = frozenset({D.RULING_UNRESOLVED, D.UNSUPPORTED, D.TECHNICAL_LIMIT})
# API が前の確かめを満たすと書く種類（GUARANTEE_PLACEMENT・GUARANTEE_MULLIGAN・GUARANTEE_TURN_ACTION・GUARANTEE_BOARD_ACTION の acceptance）。ほかは受理を保証しない
PRECHECK_KINDS = frozenset({"place_starting", "mulligan_draw", "play_basic", "attach_energy", "evolve", "retreat", "remove_disguise", "discard_from_play",
                            "reveal_face_down"})
FACE_DOWN_REASON = "face_down_reveal_not_evaluated"


def snapshot(game, hub) -> dict[str, Any]:
    state = game.state
    return {"state_object": id(state), "checks": checks(state), "outbox": {str(a): len(hub._outbox[a]) for a in AUDIENCES},
            "update_number": hub._seq, "failure": game.failure is not None}


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """変わったものの名前（空なら変化なし）。状態のオブジェクトが同じことだけで変化なしとしない（確認値も比べる）。既にあった未取得の更新は数えず、増えた分だけを見る。"""
    changed = []
    if before["state_object"] != after["state_object"]:
        changed.append("state_object_replaced")
    for key in sorted(set(before["checks"]) | set(after["checks"])):
        if before["checks"].get(key) != after["checks"].get(key):
            changed.append(f"checks.{key}")
    for audience, n in before["outbox"].items():
        if after["outbox"].get(audience, 0) > n:
            changed.append(f"new_update:{audience}")
    if after["update_number"] != before["update_number"]:
        changed.append("update_number")
    if after["failure"] != before["failure"]:
        changed.append("failure")
    return changed


def judge_negative(expected_code: str, expected_refetch: bool, responses: list[tuple[str, dict[str, Any]]], changed: list[str]) -> tuple[str, list[str]]:
    """変異の要求（check と submit）の判定。副作用があれば suspect。エンジンに渡った（受理・拒否・failed）・check が valid なら suspect。期待と違うコードは undetermined。"""
    reasons: list[str] = []
    if changed:
        return SUSPECT, ["side_effect:" + ",".join(changed)]
    verdict = EXPECTED
    for kind, resp in responses:
        if not resp.get("ok", False) and kind == "submit":
            return SUSPECT, [f"{kind}:envelope_error:{(resp.get('error') or {}).get('code')}"]
        if kind == "check":
            body = resp.get("response") or {}
            if body.get("valid"):
                return SUSPECT, ["check:valid_for_invalid_input"]
            code = (body.get("refusal") or {}).get("code")
        else:
            if resp.get("outcome") in (D.ACCEPTED, D.REJECTED, D.FAILED):
                return SUSPECT, [f"submit:reached_engine:{resp.get('outcome')}"]
            code = (resp.get("refusal") or {}).get("code")
        if code != expected_code:
            verdict = UNDETERMINED
            reasons.append(f"{kind}:code:{code}!={expected_code}")
        elif bool(resp.get("refetch_required")) != expected_refetch:
            return SUSPECT, [f"{kind}:refetch_required:{resp.get('refetch_required')}"]
    return verdict, reasons


def judge_recovery(resp: dict[str, Any], changed: list[str]) -> tuple[str, list[str]]:
    """変異のあとに、同じ取っ手で元の正常な入力を check（状態を変えない）: valid で副作用なしなら expected。"""
    if changed:
        return SUSPECT, ["side_effect:" + ",".join(changed)]
    body = resp.get("response") or {}
    if not body.get("valid"):
        return SUSPECT, [f"recovery_check_invalid:{(body.get('refusal') or {}).get('code')}"]
    return EXPECTED, []


def judge_normal(candidate: dict[str, Any], meaning: list[dict[str, Any]], submit: dict[str, Any]) -> tuple[str, list[str]]:
    """通常の進行の送信（check が valid のあと、同じ取っ手・同じ入力で、あいだに状態の変化がない）の判定（D-6 の表の 1〜3・9）。"""
    outcome = submit.get("outcome")
    if outcome == D.ACCEPTED:
        return EXPECTED, []
    if outcome == "refused":
        return SUSPECT, [f"check_valid_but_host_refused:{(submit.get('refusal') or {}).get('code')}"]
    if outcome == D.FAILED or not submit.get("ok", True):
        return SUSPECT, ["failed"]
    if outcome != D.REJECTED:
        return UNDETERMINED, [f"unknown_outcome:{outcome}"]
    diag = submit.get("verifier") or {}
    category = diag.get("category")
    if category is None or category == D.UNMAPPED:
        return SUSPECT, [f"diagnostic_unmapped:{diag.get('diagnostic_id')}"]
    catalog = _catalog_category(diag.get("engine_code"))
    if catalog is not None and catalog != category:
        return SUSPECT, [f"diagnostic_category_mismatch:{category}!={catalog}"]
    eligible = all((m.get("option") or {}).get("eligible") is not False for m in meaning)
    face_down = FACE_DOWN_REASON in (candidate.get("reasons") or [])
    if candidate.get("kind") in PRECHECK_KINDS and eligible and not face_down and candidate.get("processability") != "unverified":
        if category == D.INVALID_INPUT:
            return SUSPECT, ["precheck_guarantee_rejected_invalid_input"]
        if category in STOP_CATEGORIES and candidate.get("processability") == "supported":
            return SUSPECT, ["supported_rejected_with_stop"]
        if category not in STOP_CATEGORIES:
            return UNDETERMINED, [f"precheck_kind_category:{category}"]
    if category in STOP_CATEGORIES:
        return _known_stop_or_undetermined(candidate, meaning, diag, category, catalog)
    return NORMAL_REJECTION, [category]


def _catalog_category(code) -> str | None:
    """エンジンの元のコードの、診断のコード表の分類（コード表にないなら None）。"""
    if not code:
        return None
    entry = D.default_catalog().get(code)
    return None if entry is None else entry.category


def _known_stop_or_undetermined(candidate, meaning, diag, category, catalog) -> tuple[str, list[str]]:
    """停止系の拒否を known_stop にするのは、(1) 元のコードが診断のコード表にあり、分類が同じ、(2) その経路の候補か選んだものの理由が、エンジンの側の確かめを候補の作成では
    評価していないことを示す（EXPLAINING_REASONS）ときだけ。処理可能性の区分（may_stop_later・unverified）だけでは known_stop にしない。足りなければ undetermined。"""
    if catalog is None:
        return UNDETERMINED, [f"stop_code_not_in_catalog:{diag.get('engine_code')}"]
    reasons = set(candidate.get("reasons") or [])
    for m in meaning:
        reasons |= set((m.get("option") or {}).get("reasons") or [])
    explained = sorted(reasons & EXPLAINING_REASONS)
    if not explained:
        return UNDETERMINED, [f"stop_not_explained_by_path:{diag.get('engine_code')}"]
    return KNOWN_STOP, [category, diag.get("engine_code"), *explained]


def judge_termination(termination: str, last_accepted_processability: str | None) -> tuple[str, list[str]]:
    if termination in ("game_over", "script_complete"):
        return EXPECTED, []
    if termination == "halted_known":
        if last_accepted_processability == "supported":
            return UNDETERMINED, ["halt_after_supported"]  # supported_scope は受理のあとの完走を保証しない
        return KNOWN_STOP, []
    if termination in ("limit_operations", "limit_accepted", "limit_turns", "limit_time"):
        return EXPECTED, ["tool_limit"]
    if termination == "input_unavailable":
        return KNOWN_LIMITATION, []
    if termination in ("api_contract_unknown", "no_progress"):
        return UNDETERMINED, []
    return SUSPECT, []  # halted_unclassified・failed・state_integrity・exception・inconsistency・negative_side_effect
