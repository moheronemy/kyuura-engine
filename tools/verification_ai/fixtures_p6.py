"""P6 の追従の構築盤面（検証者の側の固定の fixture。docs/verification-ai-p6.md 5 章）。

カード固有の準備（どのカードをうらにするか・エネルギーを何枚つけるか）とケースの選び方は、このモジュールに閉じ込めます（共通の行動生成・方策・判定には入れない）。
盤面は、エンジンの P6 のテスト（``tests/test_legal_actions_p6_face_down_retreat_v0_174.py`` の ``face_down_active``）の関数で、今の実装（0.174.0）から作ります。
作ったあとの操作は公開の API（candidates・inputs・check・submit）だけで行います。通常の new_game から届いた証拠とは扱いません。旧版のスナップショットは使いません。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine import snapshot as SN
from kyuura_engine.engine import check_invariants

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "tests/test_legal_actions_p6_face_down_retreat_v0_174.py"
RATTATA, ONIX, KADABRA = "PMCG1-060", "PMCG1-054", "PMCG1-046"  # コラッタ（たね・にげる 0）・イワーク（たね・にげる 3）・ユンゲラー（1 進化）


def _board(real: str):
    from tests.test_legal_actions_p6_face_down_retreat_v0_174 import face_down_active

    return face_down_active(real)


FIXTURES: dict[str, dict[str, Any]] = {
    "P6A": {"real": RATTATA, "what": "うらのバトル場（本当のカードはたね・にげる 0）・闘エネルギー 1 枚・ベンチにエビワラー（プレイヤー 0 の番の MAIN）"},
    "P6B": {"real": ONIX, "what": "うらのバトル場（本当のカードはたね・にげる 3）・闘エネルギー 1 枚・ベンチにエビワラー"},
    "P6C": {"real": KADABRA, "what": "うらのバトル場（本当のカードは 1 進化）・闘エネルギー 1 枚・ベンチにエビワラー"},
}


def build(fixture_id: str) -> tuple[Any, dict[str, Any]]:
    """fixture を作り、(状態, 記録) を返す（記録は出典・整合の確かめ。本当のカードを含むので verifier の側だけに保存する）。"""
    spec = FIXTURES[fixture_id]
    state = _board(spec["real"])
    from tests import helpers as H

    record = {
        "fixture": fixture_id, "origin": "constructed_fixture", "new_game": False, "what": spec["what"], "real_card": spec["real"],
        "source": [{"file": SOURCE, "what": "face_down_active", "sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()},
                   {"file": "tests/test_secret_plan_v0_67.py", "what": "board・place・to_active・opponent_turn",
                    "sha256": hashlib.sha256((ROOT / "tests/test_secret_plan_v0_67.py").read_bytes()).hexdigest()}],
        "card_constant_matches_source": {name: getattr(H, name) == value for name, value in (("RATTATA", RATTATA), ("ONIX", ONIX), ("KADABRA", KADABRA))},
        "integrity": {"check_invariants": check_invariants(state), "state_usable": D.state_usable(state), "status": D.status_of(state), "phase": state.phase.value,
                      "turn": state.turn_number, "current_player": state.current_player, "snapshot_structure_problems": SN.structure_problems(state)},
    }
    return state, record


def snapshot_text(state, fixture_id: str) -> tuple[str | None, str | None]:
    try:
        snap = SN.save_snapshot(state, label=f"verification-ai P6 {fixture_id}")
    except SN.SnapshotSaveError as error:
        return None, f"{type(error).__name__}:{getattr(error, 'code', '')}"
    return SN.dumps_snapshot(snap), None


def zero_energy(tuples):
    """ケースの選び手（方策ではない）: 共通の行動生成が作った完成した入力の組から、エネルギーを 1 枚もトラッシュしない組を選ぶ。"""
    return next(i for i, (choices, _m) in enumerate(tuples) if len(choices) == 1)


def one_energy(tuples):
    """ケースの選び手: エネルギーを 1 枚トラッシュする組を選ぶ（本当のカードのにげるエネルギーに足りないことは、ケースの条件として fixture が知っている）。"""
    return next(i for i, (choices, _m) in enumerate(tuples) if len(choices) == 2)
