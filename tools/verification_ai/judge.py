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

from .actions import RETREAT_KIND, cost_not_evaluated

# 判定の規則の版。1: V3-1（8091ed6）。2: V3-2（停止系の拒否を known_stop にする条件を、診断のコード表と経路の理由で絞る。docs/verification-ai-v3-2.md 5 章）。
# 3: V3-3（known_stop には、コード・分類・経路の理由に加えて、その停止の代表の条件の根拠（KNOWN_STOP_EVIDENCE の登録と、場面の側の宣言）が要る。docs/verification-ai-v3-3.md 3 章）
# 4: P6 の追従（docs/verification-ai-p6.md 4 章）。にげるの段に cost_evaluation（費用を評価していない）がある送信の拒否を、元のコードで分ける（P6_ENGINE_DECIDES は正常な拒否、
#    P6_API_GUARANTEED は suspect、ほかは undetermined か停止の規則）。受理の中身を judge_p6_accepted で分ける。cost_evaluation のない送信の判定は規則 3 と同じ
# 5: U-R3a の追従（docs/verification-ai-u-r3a.md 3 章）。本人のうらのカードの特殊能力の送信（候補の power・pokemon に face_down、理由に face_down_reveal_not_evaluated）の
#    拒否を、元のコードと、その条件に要る段が選んだ入力にあることで分ける（FACE_DOWN_POWER_ENGINE_DECIDES は正常な拒否、FACE_DOWN_POWER_API_GUARANTEED と構造の段に
#    よる保証のコードは suspect、ほかは undetermined か停止の規則）。受理の中身を judge_face_down_power_accepted で分ける。ほかの送信（P6・おもての特殊能力をふくむ）は規則 4 と同じ
# 6: C1 の確認（docs/verification-ai-batch-plan3.md 11 章）。停止の代表の条件の根拠を、場面の側の宣言のほかに、記録した送信の API の値で確かめる道を 1 つだけ足す
#    （RECORDED_STOP_CONDITIONS。今は UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE（ER9）だけ）。recorded_stop_evidence が条件をすべて満たすときだけ根拠のコードを返し、
#    逐次バッチの判定 batch.judge_trace がそれを evidence として渡す。コードが同じでも条件を満たさない送信・ほかのコードは規則 5 と同じ（undetermined のまま）
JUDGE_RULES_VERSION = 6
# U-R3a: うらのカードの特殊能力で、エンジンがおもてにしたあとに確かめ、API が評価しないと契約で示すもの（GUARANTEE_FACE_DOWN_POWER: 構造の組は受け付けるかで絞らない）。
# 元のコード → (その条件に要る段の role（どれか 1 つが選んだ入力にあること。空なら段は問わない）, 条件の説明)。カード・効果の型ごとの登録ではない
FACE_DOWN_POWER_ENGINE_DECIDES = {
    "WRONG_ENERGY_TYPE": (("energy",), "選んだエネルギーカードのタイプが、おもてにした本当のカードの特殊能力の条件と合わない（構造の組はタイプで絞らない）"),
    "NOT_BASIC_ENERGY": (("energy",), "選んだカードが基本エネルギーカードでない（手札の並びは種類で絞らない）"),
    "SAME_POKEMON": (("source", "target"), "選んだポケモンが使うポケモン自身・移動元と移動先が同じ（構造の組は同じポケモンの組を外さない）"),
    "WRONG_POKEMON_TYPE": (("target",), "選んだポケモンのタイプが条件と合わない（場の並びはタイプで絞らない）"),
    "NO_DAMAGE_COUNTERS": (("source",), "選んだ移動元にダメージカウンターがない（場の並びはダメージで絞らない）"),
    "WOULD_KNOCK_OUT": (("target",), "移すと移動先がきぜつする（場の並びは残り HP で絞らない）"),
    "POWER_ALREADY_USED": ((), "おもてにした本当のカードのこの特殊能力を、この番にもう使った"),
}
# U-R3a: 入力の形（宣言の項目・候補を出す条件）で API が満たすもの。check が valid のあとにこの拒否があれば契約と矛盾する
FACE_DOWN_POWER_API_GUARANTEED = frozenset({"POWER_CHOICE_MISSING", "POWER_CHOICE_NOT_USED", "NOT_YOUR_TURN", "DECISION_PENDING"})
FACE_DOWN_POWER_REVEALED, FACE_DOWN_POWER_USED, FACE_DOWN_POWER_TRASHED = "secret_plan_revealed", "pokemon_power", "secret_plan_discarded"
# P6: エンジンがおもてにしたあとに確かめ、API（候補・inputs・check）が評価しないと契約で示すもの（engine._retreat → check_retreat_declaration・check_retreat の、
# 本当のカード・おもてにしたあとの状態で決まる拒否）。元のコード → その送信の条件（なぜこの経路で正常な拒否か）。カード・場面ごとの登録ではない
P6_ENGINE_DECIDES = {
    "WRONG_RETREAT_COST": "トラッシュするエネルギーの個数が、おもてにした本当のカードのにげるエネルギーと合わない（段の cost_evaluation が not_evaluated。API は費用・個数を評価していない）",
    "POKEMON_ASLEEP": "おもてにしたポケモンがねむり（うらの分岐は宣言の確かめを候補の作成で評価しない。GUARANTEE_FACE_DOWN_RETREAT の preconditions）",
    "POKEMON_PARALYZED": "おもてにしたポケモンがマヒ（同上）",
    "RETREAT_PREVENTED": "にげられない効果（同上）",
    "LEAVE_ACTIVE_PREVENTED": "バトル場をはなれられない効果（同上）",
    "RETREAT_ALREADY_FAILED": "この番にこんらんでにげるに失敗している（同上）",
}
# P6: 入力の形（候補・check）か候補を出す条件で API が満たすもの。check が valid のあとにこの拒否があれば、契約と矛盾する
P6_API_GUARANTEED = frozenset({"DUPLICATE_CARD", "ENERGY_NOT_ATTACHED", "NOT_ON_BENCH", "NO_BENCH", "NOT_YOUR_TURN", "DECISION_PENDING"})
P6_REVEALED, P6_RETREATED, P6_TRASHED = "secret_plan_revealed", "retreat", "secret_plan_discarded"
# 停止の代表の条件の根拠（V3-3 の代表例だけを明示的に扱う）。元のコード → 条件・根拠。判定は、場面の側（fixture）が同じコードの根拠を宣言したときだけ known_stop にする。
# ここにないコード・宣言のない場面の停止は undetermined（コード表にあり、経路が未評価であるだけでは、今回の停止の条件を説明したことにしない）
KNOWN_STOP_EVIDENCE = {
    "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT": {
        "condition": "ドライアップ（ファイヤーのワザ）のコインの「おもて」の数が、選んだ相手のポケモンについている「水」エネルギーより多い（受理のあとの決定の答えで止まる。DU1）",
        "source": ["tests/test_legal_actions_u7_4.py: EnergyDiscardStopTest.test_rejected_vs_stop_after_acceptance",
                   "tests/test_deferred_shortage_user_promos_v0_127.py: dry_board・run"],
    },
    # 規則 6: 逐次バッチでは、記録した送信の API の値で条件を確かめたときだけ根拠にする（RECORDED_STOP_CONDITIONS・recorded_stop_evidence）
    "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE": {
        "condition": "エネルギー回収の回収の決定（retrieve_energy。最小 0・選べる基本エネルギーカードが 1 枚以上）に 0 枚を答えた（ER9。決定は待ったまま・1 枚以上を選び直せる）",
        "source": ["docs/rules-2000-02-14.md: ER9", "docs/energy-retrieval-v0.23.md: ER9",
                   "kyuura_engine/effects.py: DiscardFromHandThenRetrieveEnergy.resume（RETRIEVE_ENERGY の min_choices 0。空の答えで UnsupportedError）",
                   "docs/stop-policy-classification.json: UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE（answer_rejection・ER9）",
                   "tests/test_energy_retrieval_v0_23.py: test_zero_cards_is_unresolved_and_keeps_the_decision"],
    },
}
# 規則 6: 記録した送信の値だけで代表の条件を確かめる停止のコード → 決定の種類（段の decision_kind）。条件は recorded_stop_evidence:
# 候補が answer_decision・段が 1 つで decision_kind が登録の種類・最小 0・最大 1 以上・選べるものが 1 つ以上・選んだものが 0・拒否で、検証者の診断と公開の結果の
# コードがそろう・拒否のあとも同じ主体の決定待ち（status awaiting_decision・next が本人の answer_decision だけ）・取り直しが要らない。カード・場面ごとの登録ではない
RECORDED_STOP_CONDITIONS = {
    "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE": "retrieve_energy",
}
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


def is_p6(candidate: dict[str, Any], stages: list[dict[str, Any]] | None) -> bool:
    """P6 の送信か: にげるの候補で、段に cost_evaluation（費用を評価していない）がある（API の契約の値だけで決める。カードでは見分けない）。"""
    return candidate.get("kind") == RETREAT_KIND and any(cost_not_evaluated(s) for s in (stages or []))


def judge_normal(candidate: dict[str, Any], meaning: list[dict[str, Any]], submit: dict[str, Any], *, evidence: str | None = None,
                 stages: list[dict[str, Any]] | None = None) -> tuple[str, list[str]]:
    """通常の進行の送信（check が valid のあと、同じ取っ手・同じ入力で、あいだに状態の変化がない）の判定（D-6 の表の 1〜3・9）。

    規則 4（P6）: ``stages`` に cost_evaluation のあるにげるの送信の拒否は、元のコードで分ける。unverified だからといって、すべての拒否を正常にしない・すべてを suspect にしない"""
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
    if is_face_down_power(candidate):
        found = _face_down_power_rejection(diag.get("engine_code"), category, catalog, meaning, stages)
        if found is not None:
            return found
        # 停止系の拒否は、規則 3 と同じく代表の条件の根拠がなければ known_stop にしない（下の _known_stop_or_undetermined）
    if is_p6(candidate, stages):
        code = diag.get("engine_code")
        if code in P6_API_GUARANTEED:
            return SUSPECT, [f"p6_structural_guarantee_rejected:{code}"]
        if code in P6_ENGINE_DECIDES and catalog is not None:
            return NORMAL_REJECTION, [category, code, "p6_engine_decides_after_reveal", "condition:" + P6_ENGINE_DECIDES[code]]
        if category not in STOP_CATEGORIES:
            return UNDETERMINED, [f"p6_rejection_not_explained:{code}"]
        # 停止系の拒否は、規則 3 と同じく代表の条件の根拠がなければ known_stop にしない（下の _known_stop_or_undetermined）
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
        return _known_stop_or_undetermined(candidate, meaning, diag, category, catalog, evidence)
    return NORMAL_REJECTION, [category]


def is_face_down_power(candidate: dict[str, Any]) -> bool:
    """本人のうらのカードの特殊能力の送信か（API の契約の値だけで決める: use_power で、power・pokemon の face_down と理由 face_down_reveal_not_evaluated）。"""
    return (candidate.get("kind") == "use_power" and (candidate.get("power") or {}).get("face_down") is True
            and (candidate.get("pokemon") or {}).get("face_down") is True and FACE_DOWN_REASON in (candidate.get("reasons") or []))


def _chosen_roles(meaning: list[dict[str, Any]], stages: list[dict[str, Any]] | None) -> set[str]:
    by_number = {s.get("stage"): s.get("role") for s in (stages or [])}
    return {by_number.get(m.get("stage")) for m in meaning} - {None}


def _face_down_power_rejection(code, category, catalog, meaning, stages) -> tuple[str, list[str]] | None:
    """規則 5: うらのカードの特殊能力の拒否。停止系は None（呼ぶ側が停止の規則で判定する）。"""
    roles = _chosen_roles(meaning, stages)
    if code in FACE_DOWN_POWER_API_GUARANTEED:
        return SUSPECT, [f"face_down_power_structural_guarantee_rejected:{code}"]
    # 構造の段の保証: 前の段の source に依存するエネルギーの段（ついているカードの並び）を選んだのに「ついていない」は契約と矛盾する
    energy_on_source = any(s.get("role") == "energy" and "depends_on_stage" in s for s in (stages or []))
    if code == "ENERGY_NOT_ATTACHED" and energy_on_source and "energy" in roles:
        return SUSPECT, ["face_down_power_structural_guarantee_rejected:ENERGY_NOT_ATTACHED"]
    if code in FACE_DOWN_POWER_ENGINE_DECIDES and catalog is not None and category not in STOP_CATEGORIES:
        needed, condition = FACE_DOWN_POWER_ENGINE_DECIDES[code]
        if needed and not roles & set(needed):
            return UNDETERMINED, [f"face_down_power_condition_without_role:{code}:{','.join(needed)}"]
        return NORMAL_REJECTION, [category, code, "face_down_power_engine_decides_after_reveal", "condition:" + condition]
    if category not in STOP_CATEGORIES:
        return UNDETERMINED, [f"face_down_power_rejection_not_explained:{code}"]
    return None


def judge_face_down_power_accepted(candidate: dict[str, Any], new_public_events: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """規則 5: うらのカードの特殊能力の受理の中身（検証者の側。受理のあとに加わった公開のログの出来事。観戦者に見えるもの）。最初の出来事が、候補のポケモンをおもてにした
    secret_plan_revealed で、そのあと同じポケモンの pokemon_power があり secret_plan_discarded がなければ「おもてにして使った」、同じポケモンの secret_plan_discarded があり
    pokemon_power がなければ「たねでないのでトラッシュ」。おもてにしていない・どちらでもない・両方なら undetermined（受理だけで正常としない）。"""
    pid = (candidate.get("pokemon") or {}).get("pokemon")
    if not new_public_events or new_public_events[0].get("kind") != FACE_DOWN_POWER_REVEALED or new_public_events[0].get("pokemon_id") != pid:
        return UNDETERMINED, [f"face_down_power_accepted_without_reveal_first:{[e.get('kind') for e in new_public_events[:2]]}"]
    revealed = new_public_events[0].get("card_id")
    used = any(e.get("kind") == FACE_DOWN_POWER_USED and e.get("pokemon_id") == pid for e in new_public_events[1:])
    trashed = any(e.get("kind") == FACE_DOWN_POWER_TRASHED and e.get("pokemon_id") == pid for e in new_public_events[1:])
    if revealed is None:
        return UNDETERMINED, ["face_down_power_revealed_card_not_public"]
    if used and not trashed:
        return EXPECTED, ["face_down_power_revealed_and_used", f"revealed:{revealed}"]
    if trashed and not used:
        return EXPECTED, ["face_down_power_revealed_not_basic_and_trashed", f"revealed:{revealed}"]
    return UNDETERMINED, [f"face_down_power_accepted_events:{[e.get('kind') for e in new_public_events]}"]


def judge_p6_accepted(new_log_kinds: list[str]) -> tuple[str, list[str]]:
    """P6 の受理の中身（検証者の側。受理のあとに加わったログの出来事の種類）: おもてにしてにげた・おもてにしたカードがたねポケモンでないので既存の処理でトラッシュした、の
    どちらかなら expected。おもてにしていない・どちらでもない・両方あるなら undetermined（受理だけで正常としない）。"""
    if not new_log_kinds or new_log_kinds[0] != P6_REVEALED:
        return UNDETERMINED, [f"p6_accepted_without_reveal_first:{new_log_kinds[:2]}"]
    retreated, trashed = P6_RETREATED in new_log_kinds, P6_TRASHED in new_log_kinds
    if retreated and not trashed:
        return EXPECTED, ["p6_revealed_and_retreated"]
    if trashed and not retreated:
        return EXPECTED, ["p6_revealed_not_basic_and_trashed"]
    return UNDETERMINED, [f"p6_accepted_events:{new_log_kinds}"]


def _catalog_category(code) -> str | None:
    """エンジンの元のコードの、診断のコード表の分類（コード表にないなら None）。"""
    if not code:
        return None
    entry = D.default_catalog().get(code)
    return None if entry is None else entry.category


def _known_stop_or_undetermined(candidate, meaning, diag, category, catalog, evidence=None) -> tuple[str, list[str]]:
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
    code = diag.get("engine_code")
    if code not in KNOWN_STOP_EVIDENCE or evidence != code:  # 規則 3: 代表の条件の根拠がなければ known_stop にしない
        return UNDETERMINED, [f"stop_condition_not_evidenced:{code}"]
    return KNOWN_STOP, [category, code, *explained, "evidence:" + KNOWN_STOP_EVIDENCE[code]["condition"]]


def recorded_stop_evidence(candidate: dict[str, Any], meaning: list[dict[str, Any]], stages: list[dict[str, Any]] | None,
                           submit: dict[str, Any]) -> str | None:
    """規則 6: 記録した送信（候補・段・選んだ意味・submit の応答と検証者の診断）の API の値だけで、RECORDED_STOP_CONDITIONS の代表の条件をすべて満たせば
    そのコードを返す（judge_normal の evidence に渡す）。どれか 1 つでも満たさない・登録のないコードなら None（コード名だけでは根拠にしない）。"""
    diag = submit.get("verifier") or {}
    result = submit.get("result") or {}
    code = diag.get("engine_code")
    kind = RECORDED_STOP_CONDITIONS.get(code)
    if kind is None or submit.get("outcome") != D.REJECTED or not (diag.get("diagnostic_id") == result.get("diagnostic_id") == code):
        return None
    if candidate.get("kind") != "answer_decision" or not stages or len(stages) != 1 or meaning:
        return None
    stage = stages[0]
    count = stage.get("count") or {}
    if (stage.get("decision_kind") != kind or count.get("min") != 0 or not isinstance(count.get("max"), int) or count["max"] < 1
            or not stage.get("options")):
        return None
    viewer = result.get("viewer")
    if (result.get("status") != "awaiting_decision" or result.get("next") != [{"kind": "answer_decision", "player": viewer}]
            or viewer not in (0, 1) or submit.get("refetch_required") is not False):
        return None
    return code


def judge_halt_after_accept(halt: dict[str, Any] | None, *, evidence: str | None = None) -> tuple[str, list[str]]:
    """受理のあとに停止した（受理の前の拒否とは別）。公開の停止の診断の分類が既知・コード表にあり、場面がそのコードの代表の条件を宣言したときだけ known_stop。"""
    halt = halt or {}
    category, code = halt.get("category"), halt.get("diagnostic_id")
    if category == D.UNMAPPED or code is None:
        return SUSPECT, [f"halt_unmapped:{code}"]
    if category not in STOP_CATEGORIES:
        return SUSPECT, [f"halt_unclassified:{category}"]
    catalog = _catalog_category(code)
    if catalog is None:
        return UNDETERMINED, [f"halt_code_not_in_catalog:{code}"]
    if catalog != category:
        return SUSPECT, [f"halt_category_mismatch:{category}!={catalog}"]
    if code not in KNOWN_STOP_EVIDENCE or evidence != code:
        return UNDETERMINED, [f"halt_condition_not_evidenced:{code}"]
    return KNOWN_STOP, [category, code, "evidence:" + KNOWN_STOP_EVIDENCE[code]["condition"]]


def judge_effects(outcome: str | None, changed: list[str]) -> tuple[str, list[str]]:
    """副作用の判定を、受理と拒否で分ける（V3-3）。拒否・断り: どれも変わらない。受理: 状態の置きかえと更新の番号の前進があって当然で（ほかの変化も正当）、
    それがなければ undetermined。受理のあとの停止・公開の更新は、無副作用の失敗と判定しない。"""
    if outcome in (D.REJECTED, "refused", None):
        return (EXPECTED, []) if not changed else (SUSPECT, ["side_effect:" + ",".join(changed)])
    if outcome == D.ACCEPTED:
        missing = [name for name in ("state_object_replaced", "update_number") if name not in changed]
        return (EXPECTED, ["accepted_changes:" + ",".join(changed)]) if not missing else (UNDETERMINED, ["accepted_without:" + ",".join(missing)])
    return SUSPECT, [f"outcome:{outcome}"]


def judge_termination(termination: str, last_accepted_processability: str | None, *, halt: dict[str, Any] | None = None,
                      evidence: str | None = None) -> tuple[str, list[str]]:
    if termination in ("game_over", "script_complete"):
        return EXPECTED, []
    if termination == "halted_known":
        if last_accepted_processability == "supported":
            return UNDETERMINED, ["halt_after_supported"]  # supported_scope は受理のあとの完走を保証しない
        return judge_halt_after_accept(halt, evidence=evidence) if halt is not None else (UNDETERMINED, ["halt_condition_not_evidenced"])
    if termination in ("limit_operations", "limit_accepted", "limit_turns", "limit_time"):
        return EXPECTED, ["tool_limit"]
    if termination == "input_unavailable":
        return KNOWN_LIMITATION, []
    if termination in ("api_contract_unknown", "no_progress"):
        return UNDETERMINED, []
    return SUSPECT, []  # halted_unclassified・failed・state_integrity・exception・inconsistency・negative_side_effect


# ---------------------------------------------------------------- 記録した値に当てる入口（単局の runner と逐次バッチで共通。規則は上と同じで、規則の版は変えない）

FACE_DOWN_POWER_EVENTS_NOT_RECORDED = "face_down_power_public_events_not_recorded"


def judge_recorded_face_down_power(entry: dict[str, Any]) -> tuple[str, list[str]]:
    """受理された本人のうらのカードの特殊能力の送信の中身を、runner が受理の直後に記録した公開のログ（``public_events_after_accept``。観戦者に見える出来事）で
    ``judge_face_down_power_accepted`` に当てる。記録がなければ（古い trace・記録の欠け）undetermined にし、推測しない。"""
    events = entry.get("public_events_after_accept")
    if events is None:
        return UNDETERMINED, [FACE_DOWN_POWER_EVENTS_NOT_RECORDED]
    return judge_face_down_power_accepted(entry["candidate"], events)


P6_EVENTS_NOT_RECORDED = "p6_public_events_not_recorded"
ACCEPTED_FACE_DOWN_POWER, ACCEPTED_P6 = "face_down_power_accepted", "p6_accepted"  # 受理の中身の判定の種類（U-R3a・P6）
ACCEPTED_CONTENT_NOT_RECORDED = (FACE_DOWN_POWER_EVENTS_NOT_RECORDED, P6_EVENTS_NOT_RECORDED)


def judge_recorded_p6(entry: dict[str, Any]) -> tuple[str, list[str]]:
    """受理された P6 の送信の中身を、runner が受理の直後に記録した公開のログ（``public_events_after_accept``）の出来事の種類の並びで、既存の ``judge_p6_accepted``
    （規則 4。変えない）に当てる。記録がなければ undetermined にし、推測しない（うらのカードの数が減ったことなどから補わない）。"""
    events = entry.get("public_events_after_accept")
    if events is None:
        return UNDETERMINED, [P6_EVENTS_NOT_RECORDED]
    return judge_p6_accepted([e.get("kind") for e in events])


def accepted_content_check(entry: dict[str, Any]) -> str | None:
    """受理の中身を判定する送信の種類（API の契約の値だけで決める。カードでは見分けない）: 受理された本人のうらのカードの特殊能力（U-R3a）・P6 のにげる。ほかは None。"""
    if (entry.get("submit") or {}).get("outcome") != D.ACCEPTED:
        return None
    if is_face_down_power(entry["candidate"]):
        return ACCEPTED_FACE_DOWN_POWER
    if is_p6(entry["candidate"], entry.get("stages")):
        return ACCEPTED_P6
    return None


def judge_recorded_accepted_content(entry: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    """受理の中身の判定の共通の入口（単局の runner と逐次バッチが同じ記録・同じ引数で呼ぶ）。(種類, 判定, 理由) か、対象でなければ None。"""
    check = accepted_content_check(entry)
    if check is None:
        return None
    verdict, why = (judge_recorded_face_down_power if check == ACCEPTED_FACE_DOWN_POWER else judge_recorded_p6)(entry)
    return check, verdict, why


def revealed_card_id(entry: dict[str, Any]) -> str | None:
    """記録した公開のログの最初の出来事が secret_plan_revealed なら、そのカード ID（観戦者に公開された値。証跡の確かめ用で、判定には使わない）。"""
    events = entry.get("public_events_after_accept") or []
    return events[0].get("card_id") if events and events[0].get("kind") == P6_REVEALED else None


def judge_run_termination(termination: str, detail: dict[str, Any] | None, trace: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """runner の終わり方の判定（``judge_termination``）に、最後に受理した候補の処理可能性と、halted_known なら公開の停止の値（runner の終わり方の詳細の ``halt``）を渡す。"""
    accepted = [e for e in trace if e.get("type") == "attempt" and (e.get("submit") or {}).get("outcome") == D.ACCEPTED]
    last = accepted[-1]["candidate"].get("processability") if accepted else None
    halt = (detail or {}).get("halt") if termination == "halted_known" and isinstance(detail, dict) else None
    return judge_termination(termination, last, halt=halt)
