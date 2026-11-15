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
# 7: LOST_TARGET の P1（docs/verification-ai-lost-target-own-face-down-design.md 5 章・6 章・13 章）。おもての使い手の特殊能力で本人のうらのカードを指定した送信の
#    UNSUPPORTED_SECRET_PLAN_LOST_TARGET の拒否を、送った本人の送信前の観測（runner の actor_logs。方策が受け取ったものと同じ）とエンジンのカードデータ・たねの判定
#    （effects.card_is_basic_in_text）で、条件 L1〜L12 をすべて確かめたときだけ根拠にする（lost_target_failure・submit_evidence）。単局の runner と逐次バッチは
#    同じ submit_evidence を呼ぶ。条件のどれかを満たさない送信（相手のうら・決定への回答・うらの使い手・すべてたね・観測や参照の欠けをふくむ）と、ほかのコードは規則 6 と同じ
# 8: LOST_TARGET の P3s（docs/verification-ai-lost-target-p3-decision-design.md 4 章・5 章・10 章。エンジン 0.181.0）。トレーナーの決定（AttachedDamageReduction の
#    select_pokemon 1 つ）への回答で本人のうらのカードを指定した UNSUPPORTED_SECRET_PLAN_LOST_TARGET の拒否を、条件 D1〜D12 をすべて確かめたときだけ、別の鍵
#    （LOST_TARGET_P3_EVIDENCE）の根拠にする（decision_lost_target_failure）。生の診断コードは変えない。照合は根拠の項目の code（なければ鍵）と元のコードが同じとき
#    だけ（既存の項目では規則 7 と同じ式）。P1 の条件・理由・basis は変えない。条件を満たさない送信（相手のうら・複数選択・ほかの効果・再開先・basis の不足をふくむ）は規則 7 と同じ
JUDGE_RULES_VERSION = 8
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
    # 規則 7: P1 だけ。根拠は lost_target_failure が L1〜L12 をすべて確かめたときだけ渡す（コードの名前だけでは渡さない。P2・P3・うらの使い手・受理後の処理の中の指定は対象外）
    "UNSUPPORTED_SECRET_PLAN_LOST_TARGET": {
        "condition": "おもての使い手の特殊能力（use_power）の source・target の場のポケモンか energy のついている場のポケモンに、送った本人の場のうらのカードを指定し、"
                     "送信前の本人の観測で、指定したうらの本当のカードの 1 つ以上がたねポケモンでない（P1。エンジンは入口で指定して、状態を変える前に止める）",
        "source": ["tests/test_lost_target_own_face_down_v0_180.py: E1〜E6",
                   "kyuura_engine/zones.py: designate_face_down・_secret_plan_keeps",
                   "kyuura_engine/engine.py: _reveal_for_action（使い手がおもてなら source・target・energy のついているポケモンの順に can_lose=False で指定）",
                   "docs/secret-plan-preflight-v0.67.md: 4 章・5 章（エンジンの未対応）",
                   "docs/verification-ai-lost-target-own-face-down-design.md: 5 章（L1〜L12）"],
    },
    # 規則 8: P3s だけ。鍵は経路の名前（LOST_TARGET_P3_EVIDENCE）で、code が元の診断コード（照合は code と元のコードで行い、生のコードは書き換えない）。
    # 根拠は decision_lost_target_failure が D1〜D12 をすべて確かめたときだけ渡す
    "UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3": {
        "code": "UNSUPPORTED_SECRET_PLAN_LOST_TARGET",
        "condition": "使っているトレーナーの効果（AttachedDamageReduction。対象を失ったら終える効果でない）の決定（本人の場のポケモンを 1 匹選ぶ select_pokemon）に、"
                     "送った本人の場のうらのカードを答え、送信前の本人の観測で、そのうらの本当のカードがたねポケモンでない（P3s。エンジンは答えの指定で、状態を変える前に止め、"
                     "同じ決定が残る）",
        "source": ["tests/test_lost_target_p3_decision_v0_181.py: E7〜E11",
                   "kyuura_engine/engine.py: _answer_decision_once・_designate_answer（ends_on_lost_target が偽なら can_lose=False）",
                   "kyuura_engine/zones.py: designate_face_down・_secret_plan_keeps",
                   "kyuura_engine/effects.py: AttachedDamageReduction（本人の場の select_pokemon・再開先 trainer・文脈なし）",
                   "docs/verification-ai-lost-target-p3-decision-design.md: 4 章（D1〜D12）"],
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
    # 規則 3: 代表の条件の根拠がなければ known_stop にしない。規則 8: 根拠の鍵は経路の名前でもよく、その項目の code（なければ鍵そのもの）が元のコードと同じときだけ
    # （既存の項目は code を持たないので、今までの「鍵 = 元のコード = 根拠」と同じ式）
    entry = KNOWN_STOP_EVIDENCE.get(evidence) if isinstance(evidence, str) else None
    if entry is None or entry.get("code", evidence) != code:
        return UNDETERMINED, [f"stop_condition_not_evidenced:{code}"]
    return KNOWN_STOP, [category, code, *explained, "evidence:" + entry["condition"]]


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


# ---------------------------------------------------------------- 規則 7: LOST_TARGET の P1（本人の送信前の観測で根拠を確かめる。検証者の側だけ）

LOST_TARGET_CODE = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET"  # kyuura_engine.zones.SECRET_PLAN_LOST_TARGET_CODE と同じ値（テストで一致を確かめる）
# 入口（engine._reveal_for_action）で指定になる段の role → 段の meaning（宣言の型 effects.POWER_INPUT_STAGES から来る値）
LOST_TARGET_ROLES = {"source": "pokemon", "target": "pokemon", "energy": "card"}
# L12: 判定の基礎（カードの定義・たねの判定・入口の指定の処理）のファイル（パッケージの中の相対パス）。記録の実装の識別（behavior_digest）が今と違うときは、
# 呼ぶ側（保存済みの記録の当て直し）が記録を作ったエンジンの同じファイルから同じ方式で計算した値（basis）を渡したときだけ、同じ基礎とみなす
LOST_TARGET_BASIS_METHOD = "kyuura-lost-target-basis-sha256/1"
LOST_TARGET_BASIS_FILES = ("cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py")
LOST_TARGET_CONDITIONS = ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "L12")


def lost_target_basis(root=None) -> dict[str, Any]:
    """L12 の判定の基礎の識別（``replay_record`` の実装の識別と同じ正規化・同じ要約の方式で、``LOST_TARGET_BASIS_FILES`` だけを要約）。``root`` はパッケージの
    ディレクトリ（省略時は今のエンジン）。"""
    from pathlib import Path

    from kyuura_engine.replay_record import PACKAGE_ROOT, _digest

    base = Path(root) if root is not None else PACKAGE_ROOT
    return {"method": LOST_TARGET_BASIS_METHOD, "files": list(LOST_TARGET_BASIS_FILES), "digest": _digest(base, LOST_TARGET_BASIS_FILES)}


def _current_basis() -> dict[str, Any]:
    global _BASIS
    if _BASIS is None:
        _BASIS = lost_target_basis()
    return _BASIS


_BASIS: dict[str, Any] | None = None


def own_view_for(actor_logs, entry: dict[str, Any]) -> dict[str, Any] | None:
    """送信 ``entry`` の主体の、送信前の本人の観測（runner がエピソードの初めに取り、方策に渡し、``actor_logs`` に残した ``view``）。主体の行のうち type が position で、
    position と episode（番号と主体）が送信と同じ行がちょうど 1 つのときだけ返す（ない・2 つ以上なら None）。``actor_logs`` は runner の結果の値か、保存した
    ``actors/<主体>.jsonl`` を主体ごとに読んだ辞書（鍵は主体の数か文字列）。"""
    actor, position, episode = entry.get("actor"), entry.get("position"), entry.get("episode")
    if not isinstance(actor_logs, dict) or actor not in (0, 1) or type(position) is not int or type(episode) is not int:
        return None
    rows = actor_logs.get(actor)
    if rows is None:
        rows = actor_logs.get(str(actor))
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, dict) and r.get("type") == "position" and r.get("position") == position
             and isinstance(r.get("episode"), dict) and r["episode"].get("episode") == episode and r["episode"].get("actor") == actor]
    return found[0].get("view") if len(found) == 1 else None


def _field_rows(observation: dict[str, Any]) -> list[tuple[int, dict[str, Any]]] | None:
    """観測の場のポケモン（持ち主, 場のポケモンの値）。players の並びと player の値が合わなければ None。"""
    players = observation.get("players")
    if not isinstance(players, list) or len(players) != 2:
        return None
    rows = []
    for owner, side in enumerate(players):
        if not isinstance(side, dict) or side.get("player") != owner:
            return None
        for z in [side.get("active"), *(side.get("bench") or [])]:
            if isinstance(z, dict):
                rows.append((owner, z))
    return rows


def _header_value(header) -> dict[str, Any] | None:
    value = header() if callable(header) else header
    return value if isinstance(value, dict) else None


def _recorded_pool_matches(header) -> dict[str, Any] | None:
    """L12・D12 が共有する依存の確かめ: 記録の header の依存（既定のカードプール・カードデータの出どころ）が今のカードプールと同じなら header の値、違えば None。"""
    from kyuura_engine.cards import load_card_pool

    header = _header_value(header)
    if header is None:
        return None
    deps = header.get("dependencies") or {}
    source = load_card_pool().source
    if deps.get("card_pool") != "default" or deps.get("card_data") != {k: source[k] for k in ("repository", "commit", "path")}:
        return None
    return header


def _same_behavior(header: dict[str, Any]) -> bool:
    """記録の実装の識別（behavior_digest。方式もふくむ）が今と同じか。"""
    from kyuura_engine.replay_record import current_identity

    engine, current = header.get("engine") or {}, current_identity()
    return engine.get("method") == current["method"] and engine.get("behavior_digest") == current["behavior_digest"]


def _basis_matches(header, basis) -> bool:
    """L12: 判定に使うカードデータ・たねの判定・入口の処理が、記録を作ったエンジンと同じか。記録の header の依存（既定のカードプール・カードデータの出どころ）が今の
    カードプールと同じで、かつ (a) 記録の実装の識別（behavior_digest）が今と同じか、(b) 呼ぶ側が渡した ``basis`` が今の基礎の識別と同じ。確かめられなければ False。"""
    header = _recorded_pool_matches(header)
    if header is None:
        return False
    if _same_behavior(header):
        return True
    expected = _current_basis()
    return isinstance(basis, dict) and basis.get("method") == expected["method"] and basis.get("digest") == expected["digest"]


def lost_target_failure(entry: dict[str, Any], *, trace: list[dict[str, Any]] | None, actor_logs, header, basis=None) -> str | None:
    """規則 7: 送信 ``entry``（trace の送信の行）が P1 の条件 L1〜L12（設計 5 章）をすべて満たすなら None、満たさない最初の条件の id を返す。

    使う値: 送信の行（候補・段・選んだ意味・submit の応答と検証者の診断）、同じ trace の同じエピソードの前の送信、本人の送信前の観測（``own_view_for``）、記録の
    header の依存と実装の識別（``header``。値か、値を返す関数）、エンジンのカードプールと ``effects.card_is_basic_in_text``。完全な記録の操作・相手の観測・replay は
    使わない。返す値は条件の id だけで、場のポケモンの番号・uid・カード ID・本当のカードを持たない（判定の理由・行・集計に入れない）。"""
    candidate, submit = entry.get("candidate") or {}, entry.get("submit") or {}
    diag, result = submit.get("verifier") or {}, submit.get("result") or {}
    actor = entry.get("actor")
    # L1: エンジンの拒否（ホストの断り・failed・エラーを除く）
    if submit.get("outcome") != D.REJECTED or submit.get("ok") is not True or submit.get("refusal") is not None or submit.get("error") is not None:
        return "L1"
    # L2: コードと分類（検証者の診断・公開の結果・コード表）
    if not (diag.get("engine_code") == diag.get("diagnostic_id") == result.get("diagnostic_id") == LOST_TARGET_CODE
            and diag.get("category") == result.get("category") == D.UNSUPPORTED == _catalog_category(LOST_TARGET_CODE)):
        return "L2"
    # L3: 拒否のあとも同じ主体の番（入口で止まった形）
    if (actor not in (0, 1) or result.get("status") != "in_progress" or result.get("continuable") is not True
            or result.get("next") != [{"kind": "turn_action", "player": actor}] or result.get("viewer") != actor or result.get("halt") is not None
            or submit.get("refetch_required") is not False):
        return "L3"
    # L4: おもての使い手の特殊能力（うらの使い手 P1u・ほかの種類を除く）。理由 face_down_reveal_not_evaluated は、候補か選んだ選べるもの（_known_stop_or_undetermined と
    # 同じ範囲）にあること（候補がおもてだけの組もふくむと、候補の理由は continuation_not_evaluated になり、うらの選べるものの側にだけ付く。設計 13 章）
    user, power = candidate.get("pokemon") or {}, candidate.get("power") or {}
    meaning = entry.get("meaning") or []
    reasons = set(candidate.get("reasons") or [])
    for m in meaning:
        reasons |= set(((m.get("option") if isinstance(m, dict) else None) or {}).get("reasons") or [])
    if (candidate.get("kind") != "use_power" or not isinstance(user.get("card_id"), str) or user.get("face_down") is True or power.get("face_down") is True
            or FACE_DOWN_REASON not in reasons or type(user.get("pokemon")) is not int):
        return "L4"
    # L5: 選んだ段が、入口で指定になる role・meaning だけ
    by_number = {s.get("stage"): s for s in (entry.get("stages") or []) if isinstance(s, dict)}
    chosen = []
    for m in meaning:
        stage = by_number.get(m.get("stage")) if isinstance(m, dict) else None
        role = (stage or {}).get("role")
        if stage is None or role not in LOST_TARGET_ROLES or stage.get("meaning") != LOST_TARGET_ROLES[role] or not isinstance(m.get("option"), dict):
            return "L5"
        chosen.append((role, m["option"]))
    if not chosen:
        return "L5"
    # L6: 送信前の本人の観測がちょうど 1 つで、送信の時点と同じ（番・段階・決定・同じエピソードの前に受理がない）
    view = own_view_for(actor_logs, entry)
    observation = (view or {}).get("observation") if isinstance(view, dict) else None
    if not isinstance(observation, dict) or view.get("ok") is not True or view.get("viewer") != actor:
        return "L6"
    from .policies import turn_of

    if (observation.get("viewer") != actor or observation.get("current_player") != actor or observation.get("phase") != "main"
            or observation.get("decision") is not None or not isinstance(entry.get("turn"), list) or list(turn_of(view)) != entry["turn"]):
        return "L6"
    if not isinstance(trace, list) or any(
            isinstance(x, dict) and x.get("type") == "attempt" and x.get("episode") == entry.get("episode") and type(x.get("n")) is int
            and x["n"] < entry.get("n", 0) and (x.get("submit") or {}).get("outcome") == D.ACCEPTED for x in trace):
        return "L6"
    rows = _field_rows(observation)
    if rows is None:
        return "L6"
    # L7: 使い手は観測の主体の場に 1 つだけあり、うらでない
    users = [(owner, z) for owner, z in rows if z.get("pokemon_id") == user["pokemon"]]
    if len(users) != 1 or users[0][0] != actor or users[0][1].get("face_down") is True:
        return "L7"
    # L8: 参照がちょうど 1 つに合い、選べるものと観測の face_down が同じ
    designated = []
    for role, option in chosen:
        if role == "energy":
            card = option.get("card")
            hits = [(owner, z) for owner, z in rows if type(card) is int
                    and any(isinstance(e, dict) and e.get("card") == card for e in (z.get("energy") or []))]
        else:
            pid = option.get("pokemon")
            hits = [(owner, z) for owner, z in rows if type(pid) is int and z.get("pokemon_id") == pid]
            if len(hits) == 1 and (option.get("face_down") is True) != (hits[0][1].get("face_down") is True):
                return "L8"
        if len(hits) != 1:
            return "L8"
        designated.append(hits[0])
    # L9: うらの指定が 1 つ以上で、すべて主体の場（相手のうらが 1 つでもあれば P2・混在なので除く）
    face_down = [(owner, z) for owner, z in designated if z.get("face_down") is True]
    if not face_down or any(owner != actor for owner, _z in face_down):
        return "L9"
    # L10: 指定したうらのすべてで、本当のカードがカードプールにあり、たねの判定が決まる（エンジンと同じ関数。複製しない）
    from kyuura_engine.cards import load_card_pool
    from kyuura_engine.effects import TEXT_PRE_NEO, card_is_basic_in_text

    definitions = load_card_pool().definitions
    answers = []
    for _owner, z in face_down:
        real = z.get("real")
        card_id = real.get("card_id") if isinstance(real, dict) else None
        definition = definitions.get(card_id) if isinstance(card_id, str) else None
        answer = None if definition is None else card_is_basic_in_text(definition, TEXT_PRE_NEO)
        if answer not in (True, False):
            return "L10"
        answers.append(answer)
    # L11: 1 つ以上がたねポケモンでない（すべてたねなら根拠の矛盾。known_stop にしない）
    if all(answers):
        return "L11"
    # L12: 判定の基礎が記録を作ったエンジンと同じ
    if not _basis_matches(header, basis):
        return "L12"
    return None


def own_face_down_lost_target_evidence(entry: dict[str, Any], *, trace, actor_logs, header, basis=None) -> str | None:
    """規則 7: P1 の条件 L1〜L12 をすべて満たせば ``LOST_TARGET_CODE``（judge_normal の evidence）、そうでなければ None。"""
    return LOST_TARGET_CODE if lost_target_failure(entry, trace=trace, actor_logs=actor_logs, header=header, basis=basis) is None else None


# ---------------------------------------------------------------- 規則 8: LOST_TARGET の P3s（決定への回答で本人のうらを指定。検証者の側だけ）

LOST_TARGET_P3_EVIDENCE = "UNSUPPORTED_SECRET_PLAN_LOST_TARGET#P3"  # KNOWN_STOP_EVIDENCE の鍵（経路の名前）。生の診断コードではない
# D7: 決定への回答で本人のうらを指定し、対象を失うと続けられない効果の型（effects の implementation_id。カード ID の一覧ではない。エンジンの登録を読んで確かめる）
LOST_TARGET_DECISION_EFFECTS = frozenset({"attached_damage_reduction"})
LOST_TARGET_P3_CONDITIONS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12")
# D12: P3 の判定の基礎（P1 の 5 ファイルに、決定の出し方 decisions.py と、答えの指定・観測の形 observation.py を足す）。正規化・要約は lost_target_basis と同じ
# （replay_record._digest。ファイルの並びは下の固定の順）
LOST_TARGET_P3_BASIS_METHOD = "kyuura-lost-target-p3-basis-sha256/1"
LOST_TARGET_P3_BASIS_FILES = ("cards.py", "data/kyuura_cards.json", "effects.py", "engine.py", "zones.py", "decisions.py", "observation.py")


def lost_target_p3_basis(root=None) -> dict[str, Any]:
    """D12 の判定の基礎の識別（``lost_target_basis`` と同じ方式で、``LOST_TARGET_P3_BASIS_FILES`` だけを要約）。``root`` はパッケージのディレクトリ（省略時は今のエンジン）。"""
    from pathlib import Path

    from kyuura_engine.replay_record import PACKAGE_ROOT, _digest

    base = Path(root) if root is not None else PACKAGE_ROOT
    return {"method": LOST_TARGET_P3_BASIS_METHOD, "files": list(LOST_TARGET_P3_BASIS_FILES), "digest": _digest(base, LOST_TARGET_P3_BASIS_FILES)}


_P3_BASIS: dict[str, Any] | None = None


def _current_p3_basis() -> dict[str, Any]:
    global _P3_BASIS
    if _P3_BASIS is None:
        _P3_BASIS = lost_target_p3_basis()
    return _P3_BASIS


def _p3_basis_matches(header, basis_p3) -> bool:
    """D12: 記録の依存が今のカードプール・カードデータ・効果の登録と同じで、(a) 実装の識別が今と同じか、(b) 呼ぶ側の ``basis_p3`` が今の P3 の基礎と同じ
    （方式・ファイルの並び・要約がすべて同じ）。P1 の basis は読まない（方式・ファイルが違うので一致とみなさない）。"""
    from kyuura_engine.effects import DEFAULT_EFFECTS

    header = _recorded_pool_matches(header)
    if header is None or (header.get("dependencies") or {}).get("effects") != DEFAULT_EFFECTS.id:
        return False
    if _same_behavior(header):
        return True
    expected = _current_p3_basis()
    return (isinstance(basis_p3, dict) and basis_p3.get("method") == expected["method"] and basis_p3.get("files") == expected["files"]
            and basis_p3.get("digest") == expected["digest"])


def decision_lost_target_failure(entry: dict[str, Any], *, trace: list[dict[str, Any]] | None, actor_logs, header, basis_p3=None) -> str | None:
    """規則 8: 送信 ``entry`` が P3s の条件 D1〜D12（設計 4.2 節）をすべて満たすなら None、満たさない最初の条件の id を返す。

    使う値は P1 と同じ範囲（送信の行・同じ trace・本人の送信前の観測 ``own_view_for``・記録の header・エンジンのカードプールと効果の登録・``card_is_basic_in_text``）。
    完全な記録・相手の観測・replay は読まない。効果を実行・再開しない。返す値は条件の id だけ（場のポケモンの番号・uid・カード ID・本当のカードを持たない）。"""
    candidate, submit = entry.get("candidate") or {}, entry.get("submit") or {}
    diag, result = submit.get("verifier") or {}, submit.get("result") or {}
    actor = entry.get("actor")
    # D1: エンジンの拒否（ホストの断り・failed・エラーを除く）
    if submit.get("outcome") != D.REJECTED or submit.get("ok") is not True or submit.get("refusal") is not None or submit.get("error") is not None:
        return "D1"
    # D2: コードと分類（検証者の診断・公開の結果・コード表）
    if not (diag.get("engine_code") == diag.get("diagnostic_id") == result.get("diagnostic_id") == LOST_TARGET_CODE
            and diag.get("category") == result.get("category") == D.UNSUPPORTED == _catalog_category(LOST_TARGET_CODE)):
        return "D2"
    # D3: 拒否のあとも同じ主体の決定待ち（同じ決定が残る形）
    if (actor not in (0, 1) or result.get("status") != "awaiting_decision" or result.get("continuable") is not True
            or result.get("next") != [{"kind": "answer_decision", "player": actor}] or result.get("viewer") != actor or result.get("halt") is not None
            or submit.get("refetch_required") is not False):
        return "D3"
    # D4: 決定への回答の候補で、理由 continuation_not_evaluated が候補か選んだ選べるもの（段の未選択の選べるものは読まない）にある
    meaning = entry.get("meaning")
    if candidate.get("kind") != "answer_decision" or not isinstance(meaning, list) or not all(isinstance(m, dict) for m in meaning):
        return "D4"
    reasons = set(candidate.get("reasons") or [])
    for m in meaning:
        reasons |= set(((m.get("option") if isinstance(m.get("option"), dict) else None) or {}).get("reasons") or [])
    if "continuation_not_evaluated" not in reasons:
        return "D4"
    # D5: 段はちょうど 1 つの select_pokemon（意味 pokemon・最小最大 1）。選べるものの値は重なりのない整数。choices・meaning はちょうど 1 つで、段の選べるものに合う
    stages = entry.get("stages")
    if not isinstance(stages, list) or len(stages) != 1 or not isinstance(stages[0], dict):
        return "D5"
    stage = stages[0]
    count = stage.get("count") or {}
    options = stage.get("options")
    if (stage.get("stage") != 1 or stage.get("input") != "choose_option" or stage.get("decision_kind") != "select_pokemon" or stage.get("meaning") != "pokemon"
            or count.get("min") != 1 or count.get("max") != 1 or not isinstance(options, list) or not options
            or not all(isinstance(o, dict) and isinstance(o.get("id"), str) and type(o.get("value")) is int for o in options)):
        return "D5"
    values = [o["value"] for o in options]
    ids = [o["id"] for o in options]
    if len(set(values)) != len(values) or len(set(ids)) != len(ids):
        return "D5"
    choices = entry.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or choices[0] not in ids or len(meaning) != 1:
        return "D5"
    chosen = options[ids.index(choices[0])]
    m = meaning[0]
    if m.get("stage") != 1 or not isinstance(m.get("option"), dict) or type(m["option"].get("value")) is not int or m["option"]["value"] != chosen["value"]:
        return "D5"
    value = chosen["value"]
    # D6: 送信前の本人の観測がちょうど 1 つで、送信の時点と同じ（決定待ち・同じ決定・同じ番・同じエピソードの前に受理がない）
    view = own_view_for(actor_logs, entry)
    observation = (view or {}).get("observation") if isinstance(view, dict) else None
    if not isinstance(observation, dict) or view.get("ok") is not True or view.get("viewer") != actor:
        return "D6"
    from .policies import turn_of

    decision = observation.get("decision")
    if (observation.get("viewer") != actor or observation.get("current_player") != actor or observation.get("phase") != "decision"
            or not isinstance(decision, dict) or not isinstance(entry.get("turn"), list) or list(turn_of(view)) != entry["turn"]):
        return "D6"
    seen = decision.get("options")
    if (decision.get("player") != actor or decision.get("kind") != stage["decision_kind"] or decision.get("meaning") != "pokemon"
            or decision.get("min_choices") != 1 or decision.get("max_choices") != 1 or not isinstance(seen, list)
            or [o.get("value") if isinstance(o, dict) else None for o in seen] != values):
        return "D6"
    if not isinstance(trace, list) or any(
            isinstance(x, dict) and x.get("type") == "attempt" and x.get("episode") == entry.get("episode") and type(x.get("n")) is int
            and x["n"] < entry.get("n", 0) and (x.get("submit") or {}).get("outcome") == D.ACCEPTED for x in trace):
        return "D6"
    rows = _field_rows(observation)
    if rows is None:
        return "D6"
    # D7: 使っているトレーナーは本人のもので、エンジンの効果の登録が表の型（対象を失ったら終える効果でない）
    from kyuura_engine.effects import DEFAULT_EFFECTS, AttachedDamageReduction

    used = observation.get("trainer_in_use")
    if not isinstance(used, dict) or used.get("player") != actor or used.get("user") != actor or not isinstance(used.get("card_id"), str):
        return "D7"
    effect = getattr(DEFAULT_EFFECTS.trainer_entry(used["card_id"]), "effect", None)
    if (not isinstance(effect, AttachedDamageReduction) or getattr(effect, "implementation_id", None) not in LOST_TARGET_DECISION_EFFECTS
            or getattr(effect, "ends_on_lost_target", None) is not False):
        return "D7"
    # D8: 決定の選べるものが、効果の resolve の形（本人の場のバトル場 → ベンチ）と同じ並び
    own = observation["players"][actor]
    active, bench = own.get("active"), own.get("bench")
    if not isinstance(active, dict) or not isinstance(bench, list) or not all(isinstance(z, dict) for z in bench):
        return "D8"
    if [z.get("pokemon_id") for z in (active, *bench)] != values:
        return "D8"
    # D9: 選んだ参照が観測の場にちょうど 1 つあり、本人の場のうら（相手のうら P3o・おもてを除く）
    hits = [(owner, z) for owner, z in rows if z.get("pokemon_id") == value]
    if len(hits) != 1 or hits[0][0] != actor or hits[0][1].get("face_down") is not True:
        return "D9"
    # D10: 本当のカードがカードプールにあり、たねの判定が決まる（P1 の L10 と同じ関数。複製しない）
    from kyuura_engine.cards import load_card_pool
    from kyuura_engine.effects import TEXT_PRE_NEO, card_is_basic_in_text

    real = hits[0][1].get("real")
    card_id = real.get("card_id") if isinstance(real, dict) else None
    definition = load_card_pool().definitions.get(card_id) if isinstance(card_id, str) else None
    answer = None if definition is None else card_is_basic_in_text(definition, TEXT_PRE_NEO)
    if answer not in (True, False):
        return "D10"
    # D11: たねポケモンでない（たね・ベイビィなら、エンジンはおもてにして続けるはずなので根拠の矛盾）
    if answer is True:
        return "D11"
    # D12: 判定の基礎が記録を作ったエンジンと同じ
    if not _p3_basis_matches(header, basis_p3):
        return "D12"
    return None


def own_face_down_decision_lost_target_evidence(entry: dict[str, Any], *, trace, actor_logs, header, basis_p3=None) -> str | None:
    """規則 8: P3s の条件 D1〜D12 をすべて満たせば ``LOST_TARGET_P3_EVIDENCE``（judge_normal の evidence。鍵の名前）、そうでなければ None。"""
    failure = decision_lost_target_failure(entry, trace=trace, actor_logs=actor_logs, header=header, basis_p3=basis_p3)
    return LOST_TARGET_P3_EVIDENCE if failure is None else None


def submit_evidence(entry: dict[str, Any], *, trace, actor_logs, header, basis=None, basis_p3=None) -> str | None:
    """送信の判定（judge_normal）に渡す根拠の共通の入口。単局の runner（変異の実行の中の判定）と逐次バッチ（batch.judge_trace）が、同じ送信の行・同じ trace・同じ
    actor_logs・同じ記録の header で呼ぶ。規則 6（recorded_stop_evidence。ER9）・規則 7（own_face_down_lost_target_evidence。P1。``basis`` だけを使う）・規則 8
    （own_face_down_decision_lost_target_evidence。P3s。``basis_p3`` だけを使う）の順に、条件をすべて満たすときだけ根拠の鍵を返す。"""
    found = recorded_stop_evidence(entry.get("candidate") or {}, entry.get("meaning") or [], entry.get("stages"), entry.get("submit") or {})
    if found is not None:
        return found
    found = own_face_down_lost_target_evidence(entry, trace=trace, actor_logs=actor_logs, header=header, basis=basis)
    if found is not None:
        return found
    return own_face_down_decision_lost_target_evidence(entry, trace=trace, actor_logs=actor_logs, header=header, basis_p3=basis_p3)


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
