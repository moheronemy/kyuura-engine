"""V3-3 の構築盤面（検証者の側の固定の fixture。docs/verification-ai-v3-3.md 4 章）。

カード固有の準備はこのモジュールに閉じ込めます（共通の行動生成・方策・判定には入れない）。盤面は既存のテストの関数（``tests/``）で作ります: 作るときにだけ内部の状態を使い、
作ったあとの操作は公開の API（candidates・inputs・check・submit）だけで行います。通常の new_game から届いた証拠とは扱いません。

各 fixture は、出典（ファイル・関数・ファイルの sha256）・出典からの変更・整合の確かめ（``engine.check_invariants``・``diagnostics.state_usable``・スナップショットの保存と復元）を
記録します。意図的に不整合にした盤面は使いません。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine import snapshot as SN
from kyuura_engine.engine import check_invariants

ROOT = Path(__file__).resolve().parents[2]
MANKEY = "PMCG2-028"  # マンキー（ジャングル。たね。［スパイ］: 入力なし。受理のあとに見るカードを選ぶ決定）
UNOWN_B = "neo3-032"  # アンノーンB（たね。［ベアー］: 自分の場のポケモン 1 匹を選ぶ 1 段）


def _sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def _f1():
    from tests import test_secret_plan_v0_67 as S

    return S.place(S.board(hand=(MANKEY,)), MANKEY)


def _f2():
    from tests import test_secret_plan_v0_67 as S

    return S.place(S.board(hand=(UNOWN_B,)), UNOWN_B)


def _f3():
    from tests import helpers as H
    from tests import test_deferred_shortage_user_promos_v0_127 as T127

    return H.with_coin_bits(T127.dry_board(2), *T127.run(3))


def _f4():
    from tests import test_legal_actions_u7_5f as T5F

    return T5F.flashed()


FIXTURES: dict[str, dict[str, Any]] = {
    "F1": {"build": _f1, "source": [("tests/test_legal_actions_u7_5g_face_down_power.py", "placed(MANKEY)・test_basic_card_reveals_then_uses_the_power_with_a_later_decision"),
                                    ("tests/test_secret_plan_v0_67.py", "board・place（apply_command でマチスの秘策を使い、マンキーをうらにしてベンチに出す）")],
           "changes": "なし（出典の盤面そのまま。プレイヤー 0 の番の MAIN）", "card_check": ("JUNGLE_MANKEY", MANKEY)},
    "F2": {"build": _f2, "source": [("tests/test_legal_actions_u7_5g_face_down_power.py", "placed(UNOWN_B)・test_rejected_after_reveal_leaves_the_state_unchanged"),
                                    ("tests/test_secret_plan_v0_67.py", "board・place")],
           "changes": "なし（出典の盤面そのまま）"},
    "F3": {"build": _f3, "source": [("tests/test_legal_actions_u7_4.py", "EnergyDiscardStopTest.test_rejected_vs_stop_after_acceptance"),
                                    ("tests/test_deferred_shortage_user_promos_v0_127.py", "dry_board(2)・run(3)"), ("tests/helpers.py", "with_coin_bits")],
           "changes": "出典と同じく、次のコインを「おもて 3・うら 1」にした乱数（テストの乱数の仕込み。with_coin_bits。盤面の不整合ではない）"},
    "F4": {"build": _f4, "source": [("tests/test_legal_actions_u7_5f.py", "flashed()（build_test_state の盤面から apply_command でフラッシュを使い、答えて番を終える）")],
           "changes": "なし（出典の盤面そのまま。おもてにする状態を直接置く built() は使わない）"},
}


def build(fixture_id: str) -> tuple[Any, dict[str, Any]]:
    """fixture を作り、(状態, 記録) を返す。記録は出典・変更・整合の確かめ・スナップショットの保存の結果。"""
    spec = FIXTURES[fixture_id]
    state = spec["build"]()
    problems = check_invariants(state)
    record: dict[str, Any] = {
        "fixture": fixture_id, "origin": "constructed_fixture", "new_game": False,
        "source": [{"file": f, "what": w, "sha256": _sha256(f)} for f, w in spec["source"]], "changes": spec["changes"],
        "integrity": {"check_invariants": problems, "state_usable": D.state_usable(state), "status": D.status_of(state), "phase": state.phase.value,
                      "turn": state.turn_number, "current_player": state.current_player, "snapshot_structure_problems": SN.structure_problems(state)},
    }
    if "card_check" in spec:  # 写した定数が出典の名前の定数と同じ（テストの名前の定数を実行の入力にしない）
        from tests import helpers as H

        name, value = spec["card_check"]
        record["integrity"]["card_constant_matches_source"] = getattr(H, name) == value
    return state, record


def snapshot_text(state, fixture_id: str) -> tuple[str | None, str | None]:
    """開始のスナップショットの JSON（保存できなければ None と理由）。"""
    try:
        snap = SN.save_snapshot(state, label=f"verification-ai V3-3 {fixture_id}")
    except SN.SnapshotSaveError as error:
        return None, f"{type(error).__name__}:{getattr(error, 'code', '')}"
    return SN.dumps_snapshot(snap), None


def restore(text: str):
    """スナップショットから、ホストの対戦（``snapshot.RestoredGame``。完全な再現用記録は持たない）を作る。"""
    report = SN.restore_snapshot(text)
    if report.status != SN.RESTORED:
        return None, report.status
    return SN.RestoredGame(report), report.status
