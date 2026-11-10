"""U-R3a の追従の構築盤面（検証者の側の固定の fixture。docs/verification-ai-u-r3a.md 5 章）。

カード固有の準備（どのカードをうらにするか・どのエネルギーをつけるか）とケースの選び方（どの組を送るか）は、このモジュールに閉じ込めます（共通の行動生成・方策・判定には
入れない）。盤面はエンジンの U-R3a のテスト（``tests/test_legal_actions_u_r3a_v0_175.py`` の ``placed``）の関数で、実行するときのエンジンの実装から作ります（U-R3a の追従の実行 u-r3a-ai-follow のときは 0.175.0。0.176.0 では PT-5e の補完のあとの実装。版と実装の識別は実行の記録に残る）。作ったあとの操作は
公開の API（candidates・inputs・check・submit）だけで行います。通常の new_game から届いた証拠とは扱いません。旧版のスナップショットは使いません。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine import snapshot as SN
from kyuura_engine.engine import check_invariants

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "tests/test_legal_actions_u_r3a_v0_175.py"
ROCKET_CHARMANDER, VENUSAUR = "PMCG4-012", "PMCG1-011"  # ロケット団のヒトカゲ（たね・2 段）・フシギバナ（2 進化・3 段）
HITMONCHAN, RATTATA, FIRE, FIGHTING = "PMCG1-058", "PMCG1-060", "PMCG1-098", "PMCG1-102"

FIXTURES: dict[str, dict[str, Any]] = {
    "UR3A-RC": {"real": ROCKET_CHARMANDER, "what": "ベンチにうらのロケット団のヒトカゲ（何もついていない）、バトル場に闘エネルギー 2 枚のエビワラー、ベンチに炎・水エネルギーのコラッタ"
                                                   "（プレイヤー 0 の番の MAIN）"},
    "UR3A-VN": {"real": VENUSAUR, "what": "同じ盤面で、うらのカードの本当のカードがフシギバナ"},
}


def build(fixture_id: str) -> tuple[Any, dict[str, Any]]:
    """fixture を作り、(状態, 記録) を返す（記録は出典・整合の確かめ。本当のカードを含むので verifier の側だけに保存する）。"""
    from tests import helpers as H
    from tests.test_legal_actions_u_r3a_v0_175 import placed

    spec = FIXTURES[fixture_id]
    state = placed(spec["real"])  # placed の中で、うらのカードに何もついていない・ダメージ 0・決定待ちでない・番がプレイヤー 0 を確かめる
    fd = [q for q in state.players[0].in_play() if state.is_face_down(q)]
    record = {
        "fixture": fixture_id, "origin": "constructed_fixture", "new_game": False, "what": spec["what"], "real_card": spec["real"],
        "source": [{"file": SOURCE, "what": "placed", "sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()},
                   {"file": "tests/test_secret_plan_v0_67.py", "what": "board・place（build_test_state のあと、マチスの秘策の PlayTrainer と ResolveDecision を apply_command）",
                    "sha256": hashlib.sha256((ROOT / "tests/test_secret_plan_v0_67.py").read_bytes()).hexdigest()}],
        "changes_from_source": "なし（テストの関数をそのまま呼ぶ）",
        "card_constant_matches_source": {name: getattr(H, name) == value for name, value in
                                         (("ROCKET_CHARMANDER", ROCKET_CHARMANDER), ("VENUSAUR", VENUSAUR), ("HITMONCHAN", HITMONCHAN), ("RATTATA", RATTATA),
                                          ("FIRE", FIRE), ("FIGHTING", FIGHTING))},
        "integrity": {"check_invariants": check_invariants(state), "state_usable": D.state_usable(state), "status": D.status_of(state), "phase": state.phase.value,
                      "turn": state.turn_number, "current_player": state.current_player, "decision": None if state.decision is None else state.decision.kind,
                      "face_down": [{"pokemon_id": q.pokemon_id, "energy": list(q.energy), "damage": q.damage} for q in fd],
                      "snapshot_structure_problems": SN.structure_problems(state)},
    }
    return state, record


def snapshot_text(state, fixture_id: str) -> tuple[str | None, str | None]:
    try:
        snap = SN.save_snapshot(state, label=f"verification-ai U-R3a {fixture_id}")
    except SN.SnapshotSaveError as error:
        return None, f"{type(error).__name__}:{getattr(error, 'code', '')}"
    return SN.dumps_snapshot(snap), None


# ケースの選び手（方策ではない）: 共通の行動生成が作った完成した入力の組 (choices, meaning) から、ケースの条件に合う組を、選べるものの公開の値（カード id・場所）で選ぶ。
def _pick(tuples, wanted: list[tuple[str, str]]) -> int:
    """``wanted`` は段の順の (場所かカードの種類, カード id)。場所は zone、カードは "card"。合う組がなければ例外（ケースが成り立たない）。"""
    for i, (_choices, meaning) in enumerate(tuples):
        options = [m["option"] for m in meaning]
        if len(options) == len(wanted) and all(o.get("card_id") == cid and (where == "card" or o.get("zone") == where)
                                               for o, (where, cid) in zip(options, wanted)):
            return i
    raise LookupError(f"no tuple for {wanted}")


def rattata_fire(tuples) -> int:
    """ヒトカゲ: ベンチのコラッタについている炎エネルギー（受理される条件をケースが知っている）。"""
    return _pick(tuples, [("bench", RATTATA), ("card", FIRE)])


def hitmonchan_fighting(tuples) -> int:
    """ヒトカゲ: バトル場のエビワラーについている闘エネルギー（形は合うが、おもてにしたあと炎でないので拒否される条件をケースが知っている）。"""
    return _pick(tuples, [("active", HITMONCHAN), ("card", FIGHTING)])


def hitmonchan_fighting_hitmonchan(tuples) -> int:
    """フシギバナ（3 段）: エビワラー → 闘エネルギー → エビワラー（受け付けるかで絞らない構造の組。本当のカードがたねでないのでトラッシュされる条件をケースが知っている）。"""
    return _pick(tuples, [("active", HITMONCHAN), ("card", FIGHTING), ("active", HITMONCHAN)])
