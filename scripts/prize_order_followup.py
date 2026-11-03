#!/usr/bin/env python3
"""v0.139 のサイドを取る順番の追加検証（docs/prize-order-followup.md）。エンジンの動作は変えない。

3 つの検証の再現を実行し、その結果（``evidence``）を docs/prize-order-followup.json に書く・記録と比べる。

- ``knowledge``（1 章）: うらのサイドを本人だけが知っている盤面・相手の手札が見える盤面で、取る順番だけを変えたときの、後に取るプレイヤーの
  決定の時点の観測（合法な選択・新しく見えたカード）と結果
- ``units``（2 章）: 2 枚対 1 枚・2 枚対 2 枚で、v0.139 の「1 枚ごとに次の人を選ぶ」（B）で届く取る順番と、「最初にプレイヤーの順番を決め、
  まとめて取る」（A）で届く順番・決定の数・最後の盤面
- ``compat``（3 章）: v0.139 の状態の写し（pickle）・書き出し（形式 34）を、比べる旧版（v0.138。``git archive`` で取り出した読み取り用の木）の
  別のプロセスで読み込み・再開したときの結果

**比較用の改変**: v0.139 は、おもてのサイドがないと順番の決定（``prize_order``）を出さない。順番だけを変えた比較のために、このスクリプトの中だけで
``resolution.prize_order_matters``（とそれを呼ぶ ``flow`` の名前）を、両方が残っていれば真を返す関数に一時的に置きかえる（``forced_order``）。
エンジンのファイルは変えない。置きかえた状態は比較にだけ使い、エンジンの今の動き（現行の契約）としては記録しない。

v0.140（docs/prize-order-user-rule-v0.140.md 6 章）: 利用者の指定でエンジンの順番の決定を改めた（prize_order → prize_first）。このスクリプトは記録を作ったコミット d631038 の
エンジン（v0.139 と同じ）の動きを前提にするので、今のエンジンでは再現を作らずに止まる（``_require_recorded_engine``）。記録の再現は、d631038 の木で動かす
（tests/test_prize_order_followup.py の ``run_in_recorded_tree``）。

使い方::

    python scripts/prize_order_followup.py --check     # 記録（docs/prize-order-followup.json の evidence）と今の再現が一致するか
    python scripts/prize_order_followup.py --write     # evidence を書き直す（ほかの項目は手で書く）
    python scripts/prize_order_followup.py --print     # 再現の結果を表示するだけ
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import pickle
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "prize-order-followup.json"
OLD_COMMIT = "4ded41817ef9a64ba07d3e0d2819d3b9cf06d318"  # v0.138（0.138.0）。v0.139 の基点
OLD_VERSION = "0.138.0"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SELFDESTRUCT = 1  # コイルの「じばく」（相手の対戦ポケモンに 40・自分に 40・お互いのベンチに 10）


# ---------------------------------------------------------------- 共通


def _imports():
    from kyuura_engine import (
        EndTurn,
        ResolveDecision,
        UseAttack,
        apply_command,
        check_invariants,
        observe,
        state_to_dict,
        visible_log,
    )
    from kyuura_engine.commands import UsePokemonPower
    from tests import helpers as H
    return EndTurn, ResolveDecision, UseAttack, UsePokemonPower, apply_command, check_invariants, observe, state_to_dict, visible_log, H


@contextlib.contextmanager
def forced_order():
    """比較用の改変（このスクリプトの中だけ）: 残りの並びに両方のプレイヤーがいれば、おもてのサイドがなくても順番の決定を出す。"""
    from kyuura_engine import resolution
    from kyuura_engine.resolution import flow
    original = flow.prize_order_matters

    def always(state, queue):
        return len(set(queue)) >= 2

    flow.prize_order_matters = always
    resolution.prize_order_matters = always
    try:
        yield
    finally:
        flow.prize_order_matters = original
        resolution.prize_order_matters = original


def _answer(state, choice):
    _, ResolveDecision, _, _, apply_command, check_invariants, *_ = _imports()
    d = state.decision
    new = apply_command(state, ResolveDecision(d.player, d.id, (choice,)))
    problems = check_invariants(new)
    if problems:
        raise AssertionError(problems)
    return new


def _cid(state, uid):
    return state.cards[uid].card_id


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _board_digest(state) -> str:
    """場・手札・サイド・山札・トラッシュの中身（決定の番号とログを除く）。カードの動きが同じかを比べる。"""
    return _digest([{"hand": sorted(p.hand), "prizes": list(p.prizes), "deck": list(p.deck), "discard": sorted(p.discard)} for p in state.players])


# ---------------------------------------------------------------- 1 章: 本人だけが知るうらのサイド


def knowledge_board(*, omanyte: bool, spy: str | None):
    """盤面を直接作った状態（P1 の番）から、合法なコマンドで P0 の番のじばくまで進める。

    - P0: コイル（雷 2）・ベンチにコイル。サイド [なにかの化石, 雷, 雷]（位置 0 のなにかの化石を P0 が取る）
    - P1: マンキー（PMCG2-028。［スパイ］。HP 30）・ベンチにコラッタ（と、``omanyte`` なら、なにかの化石から進化したオムナイト PMCG3-015 の［おみとおし］）。
      サイド [ピッピ人形, 水, 水]
    - ``spy``: P1 の番に［スパイ］で見る場所（``"own"``: 自分のサイドの位置 0・``"opponent"``: 相手のサイドの位置 0・None: 使わない）。そのあと番を終える
    - P0 の番: じばく → 両方のバトル場がきぜつし、P0 が 1 枚・P1 が 1 枚取る（並び (0, 1)）。どのサイドもうら
    """
    EndTurn, _, UseAttack, UsePokemonPower, apply_command, check_invariants, *_, H = _imports()
    bench1 = [H.RATTATA] + ([{"card": H.OMANYTE, "evolved_from": H.MYSTERIOUS_FOSSIL}] if omanyte else [])
    state = H.build_test_state([
        {"active": {"card": H.MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]}, "bench": [H.MAGNEMITE],
         "prizes": [H.MYSTERIOUS_FOSSIL, H.LIGHTNING, H.LIGHTNING], "deck": [H.LIGHTNING] * 5},
        {"active": H.JUNGLE_MANKEY, "bench": bench1, "prizes": [H.CLEFAIRY_DOLL, H.WATER, H.WATER], "deck": [H.WATER] * 5},
    ], current_player=1, turn_number=4)
    if spy is not None:
        mankey = state.players[1].active
        state = apply_command(state, UsePokemonPower(1, mankey.pokemon_id, 0))
        targets = state.decision.context_value("targets")
        owner = 1 if spy == "own" else 0
        state = _answer(state, next(i for i, t in enumerate(targets) if tuple(t[:3]) == ("prize", owner, 0)))
    state = apply_command(state, EndTurn(1))
    if check_invariants(state):
        raise AssertionError(check_invariants(state))
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


LEGAL_SEED = 2  # 下の条件に合う最初の seed（0 から順に探した。docs/prize-order-followup.md 1.3 節）
LEGAL_DECK0 = {"PMCG1-036": 4, "PMCG1-100": 56}  # コイル ×4・雷 ×56
LEGAL_DECK1 = {"PMCG1-060": 4, "PMCG3-046": 4, "PMCG3-015": 4, "PMCG1-099": 48}  # コラッタ ×4・なにかの化石 ×4・オムナイト ×4・水 ×48


def legal_omanyte_board():
    """new_game(seed 2) からの合法な操作の列: 対戦準備（``finish_setup``。ジャンケンは P0 の勝ち）→ 1 番 P0 雷をつける → 2 番 P1 なにかの化石をベンチに出す →
    3 番 P0 雷をつける → 4 番 P1 なにかの化石をオムナイトに進化させる（［おみとおし］で P0 の手札が全員に見える）→ 5 番 P0 じばく。両方のバトル場（コイル・コラッタ）が
    きぜつし、P0 が 1 枚・P1 が 1 枚取る。どのサイドもうら。"""
    from kyuura_engine import (
        AttachEnergy,
        EvolvePokemon,
        PlayTrainer,
        expand_decklist,
        new_game,
    )
    EndTurn, _, UseAttack, _, apply_command, *_, H = _imports()

    def card(state, player, card_id):
        return next(u for u in state.players[player].hand if _cid(state, u) == card_id)

    state = H.finish_setup(new_game(expand_decklist(LEGAL_DECK0), expand_decklist(LEGAL_DECK1), LEGAL_SEED), janken_winner=0)
    state = apply_command(apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card)), EndTurn(0))
    state = apply_command(apply_command(state, PlayTrainer(1, card(state, 1, "PMCG3-046"))), EndTurn(1))
    state = apply_command(apply_command(state, AttachEnergy(0, card(state, 0, "PMCG1-100"), state.players[0].active.card)), EndTurn(0))
    fossil = next(b for b in state.players[1].bench if _cid(state, b.card) == "PMCG3-046")
    state = apply_command(apply_command(state, EvolvePokemon(1, card(state, 1, "PMCG3-015"), fossil.pokemon_id)), EndTurn(1))
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


def _seen_card_ids(view, log, viewer) -> list[str]:
    """``viewer`` の観測（盤面とログ）で、相手の手札・取ったサイドとして見えているカード id。"""
    seen = []
    other = view["players"][1 - viewer]
    if other["hand"]["cards"] is not None:
        seen += sorted(c["card_id"] for c in other["hand"]["cards"])
    seen += [e["card_id"] for e in log if e.get("kind") == "take_prize" and e.get("player") != viewer and e.get("card_id")]
    return seen


def _own_known_positions(log, viewer) -> list[list]:
    """``viewer`` が見た自分のサイドの (位置, カード id)（ログ look_at_card）。"""
    return [[e["position"], e.get("card_id")] for e in log if e.get("kind") == "look_at_card" and e.get("player") == viewer and e.get("zone") == "prize"
            and e.get("owner") == viewer]


def _opponent_known_positions(log, viewer) -> list[list]:
    return [[e["position"], e.get("card_id")] for e in log if e.get("kind") == "look_at_card" and e.get("player") == viewer and e.get("zone") == "prize"
            and e.get("owner") != viewer]


def _with_card_ids(state, log):
    """ログの uid のうち見えているもの（``card``）にカード id を添える（比べやすくするため）。"""
    out = []
    for e in log:
        e = dict(e)
        if isinstance(e.get("card"), int):
            e["card_id"] = _cid(state, e["card"])
        out.append(e)
    return out


def info_policy(state, view, log, viewer):
    """見えた情報で選び方を変える方策の例（反例のため。両方のプレイヤーが使う）: 相手の手札・相手が取ったサイドになにかの化石が見えていて、自分のサイドの
    位置 0 を知っていれば位置 0、そうでなければ最後の位置を取る。"""
    known = _own_known_positions(log, viewer)
    if "PMCG3-046" in _seen_card_ids(view, log, viewer) and any(pos == 0 for pos, _ in known):
        return 0
    return state.decision.options[-1]


def _take_point(state, player):
    """``player`` が自分のサイドを選ぶ決定の時点の観測の要約。"""
    *_, observe, _, visible_log, _ = _imports()
    view = observe(state, player)
    log = _with_card_ids(state, visible_log(state, player))
    spectator = observe(state, None)
    return view, log, {
        "options": [o["value"] for o in view["decision"]["options"]],
        "seen_opponent_cards": _seen_card_ids(view, log, player),
        "known_own_positions": _own_known_positions(log, player),
        "known_opponent_positions": _opponent_known_positions(log, player),
        "take_prize_fields_seen": sorted({k for e in log if e.get("kind") == "take_prize" and e.get("player") != player for k in e if k != "kind"}),
        "spectator_seen_hands": [None if q["hand"]["cards"] is None else sorted(c["card_id"] for c in q["hand"]["cards"]) for q in spectator["players"]],
    }


def run_knowledge(omanyte: bool, spy: str | None, builder=None) -> dict:
    """順番だけを変えて（比較用の改変 ``forced_order``）、それぞれのプレイヤーが自分のサイドを選ぶ時点の観測と選択・結果を比べる。P0 はどちらの順番でも位置 0
    （なにかの化石）を取り、P1 は方策 ``info_policy`` で選ぶ。"""
    record = {"omanyte": omanyte, "spy": spy, "repro": "constructed_board_then_legal_commands" if builder is None else "legal_ops_from_new_game"}
    if builder is None:
        def builder():
            return knowledge_board(omanyte=omanyte, spy=spy)
    natural = builder()
    d = natural.decision
    record["v0139_first_decision"] = [d.kind, d.player, list(d.context_value("remaining"))]
    orders = {}
    with forced_order():
        start = builder()
        for first in (0, 1):
            s = _answer(start, first)
            points = {}
            for player in (first, 1 - first):
                if (s.decision.kind, s.decision.player) != ("take_prize", player):
                    raise AssertionError((s.decision.kind, s.decision.player, player))
                view, log, point = _take_point(s, player)
                point["pick"] = 0 if player == 0 else info_policy(s, view, log, player)  # P0 はいつも位置 0、P1 は見えた情報で選ぶ
                s = _answer(s, point["pick"])
                point["took"] = _cid(s, s.players[player].hand[-1])
                points[str(player)] = point
            orders[str(first)] = {"players": points, "board": _board_digest(s)}
    record["orders"] = orders
    record["information_differs_by_order"] = {
        str(p): {k: orders["0"]["players"][str(p)][k] != orders["1"]["players"][str(p)][k]
                 for k in ("options", "seen_opponent_cards", "known_own_positions", "known_opponent_positions")} for p in (0, 1)}
    record["choice_differs_by_order"] = {str(p): orders["0"]["players"][str(p)]["pick"] != orders["1"]["players"][str(p)]["pick"] for p in (0, 1)}
    record["board_differs_by_order"] = orders["0"]["board"] != orders["1"]["board"]
    return record


KNOWLEDGE_CASES = (
    ("K1-none", False, None),           # だれもサイドを知らない
    ("K2-spy-own", False, "own"),       # P1 が自分のサイドの位置 0 を知っている（本人だけ）
    ("K3-spy-opponent", False, "opponent"),  # P1 が P0 のサイドの位置 0 を知っている（P0 が取るカード）
    ("K4-omanyte", True, None),         # P1 の［おみとおし］で P0 の手札が全員に見える
    ("K5-omanyte-spy-own", True, "own"),  # K4 と K2 の重なり（反例の候補）
)


def knowledge_evidence() -> dict:
    out = {name: run_knowledge(omanyte, spy) for name, omanyte, spy in KNOWLEDGE_CASES}
    out["K4L-omanyte-legal"] = run_knowledge(True, None, legal_omanyte_board)
    out["K4L-omanyte-legal"]["config"] = {"seed": LEGAL_SEED, "deck0": LEGAL_DECK0, "deck1": LEGAL_DECK1, "janken_winner": 0}
    return out


# ---------------------------------------------------------------- 2 章: 複数枚を取るときの順番の単位


def units_board(case: str):
    """盤面を直接作った状態と合法なじばく。P1 のサイドの位置 1 をおもてにする（v0.139 が順番の決定を出す場面）。

    - ``"2v1"``: P1 のバトル場とダメージ 20 の控えのコラッタがきぜつ（P0 が 2 枚）・P0 のコイルがきぜつ（P1 が 1 枚）。並び (0, 0, 1)
    - ``"2v2"``: さらに P0 のダメージ 30 の控えのコイルもきぜつ（P1 が 2 枚）。並び (0, 0, 1, 1)
    - ``"2v1-last"``: ``"2v1"`` で P1 のサイドが 1 枚（P1 が途中で 0 枚になる。勝ち負けを途中で判定しないことの確かめ）
    """
    _, _, UseAttack, _, apply_command, *_, H = _imports()
    from kyuura_engine.zones import reveal_prize
    bench0 = [H.MAGNEMITE] if case != "2v2" else [{"card": H.MAGNEMITE, "damage": 30}, H.MAGNEMITE]
    prizes1 = [H.WATER, H.RATTATA, H.LIGHTNING] if case != "2v1-last" else [H.RATTATA]
    state = H.build_test_state([
        {"active": {"card": H.MAGNEMITE, "energy": [H.LIGHTNING, H.LIGHTNING]}, "bench": bench0, "prizes": [H.LIGHTNING, H.RATTATA, H.WATER],
         "deck": [H.LIGHTNING] * 5},
        {"active": H.RATTATA, "bench": [{"card": H.RATTATA, "damage": 20}, H.RATTATA], "prizes": prizes1, "deck": [H.WATER] * 5},
    ])
    reveal_prize(state, 1, 1 if case != "2v1-last" else 0, trainer=0)
    return apply_command(state, UseAttack(0, SELFDESTRUCT))


def _explore(state, path, out):
    """順番の決定のすべての答えをたどる（サイドは位置 0 を取る）。``path`` は (種類, 決めるプレイヤー, 答え, そのときの観測の要約)。"""
    *_, observe, _, visible_log, _ = _imports()
    d = state.decision
    if d is None or d.kind not in ("prize_order", "take_prize"):
        takes = [e["player"] for e in state.log if e.get("kind") == "take_prize"]
        out.append({"takes": takes, "decisions": [p[0] for p in path].count("prize_order"),
                    "info": [p[3] for p in path if p[0] == "take_prize"],
                    "result": None if state.result is None else state.result.outcome,
                    "next": None if d is None else [d.kind, d.player],
                    "board": _board_digest(state)})
        return
    if d.kind == "prize_order":
        for choice in d.options:
            _explore(_answer(state, choice), path + [("prize_order", d.player, choice, None)], out)
        return
    view = observe(state, d.player)
    seen = sorted(e["card_id"] for e in _with_card_ids(state, visible_log(state, d.player))
                  if e.get("kind") == "take_prize" and e.get("player") != d.player and e.get("card_id"))
    mid_result = None if state.result is None else state.result.outcome
    _explore(_answer(state, 0), path + [("take_prize", d.player, 0, {"player": d.player, "seen_opponent_taken": seen,
                                                                    "result_before": mid_result,
                                                                    "own_prizes": view["players"][d.player]["prizes"]["count"]})], out)


def run_units(case: str) -> dict:
    leaves = []
    start = units_board(case)
    d = start.decision
    _explore(start, [], leaves)
    queue = list(d.context_value("remaining"))
    sequences = sorted({tuple(leaf["takes"]) for leaf in leaves})
    a_sequences = sorted({tuple(sorted(queue, key=lambda p: (p != first))) for first in sorted(set(queue))})
    return {
        "queue": queue,
        "first_decision": [d.kind, d.player],
        "B_sequences": [list(s) for s in sequences],
        "A_sequences": [list(s) for s in a_sequences],
        "B_only": [list(s) for s in sequences if s not in a_sequences],
        "B_decisions_per_path": sorted({leaf["decisions"] for leaf in leaves}),
        "A_decisions": 1,
        "boards_identical": len({leaf["board"] for leaf in leaves}) == 1,
        "results": sorted({str(leaf["result"]) for leaf in leaves}),
        "next_after_takes": sorted({json.dumps(leaf["next"]) for leaf in leaves}),
        "result_before_each_take": sorted({str(i["result_before"]) for leaf in leaves for i in leaf["info"]}),
        "paths": [{"takes": leaf["takes"], "decisions": leaf["decisions"], "info": leaf["info"]} for leaf in leaves],
    }


def units_evidence() -> dict:
    return {case: run_units(case) for case in ("2v1", "2v2", "2v1-last")}


# ---------------------------------------------------------------- 3 章: 保存形式 34 の互換性

COMPAT_CHILD = r'''
import json, pickle, sys, pathlib, io, contextlib
tree, payload_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, tree)
import kyuura_engine
assert pathlib.Path(kyuura_engine.__file__).resolve().is_relative_to(pathlib.Path(tree).resolve()), kyuura_engine.__file__
from kyuura_engine import ResolveDecision, apply_command, check_invariants, observe, state_to_dict
from kyuura_engine.rng import rng_fingerprint
payload = json.loads(pathlib.Path(payload_path).read_text(encoding="utf-8"))
out = {"engine_version": kyuura_engine.__version__, "cases": {}}
def fp(state):
    import hashlib
    return hashlib.sha256(json.dumps(state_to_dict(state, format_version=34), ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]
def err(e):
    return {"type": type(e).__name__, "code": getattr(e, "code", None), "message": str(e)[:300]}
for name, case in payload.items():
    r = {}
    try:
        state = pickle.loads(bytes.fromhex(case["pickle"]))
        r["unpickle"] = "ok"
    except Exception as e:
        r["unpickle"] = err(e); out["cases"][name] = r; continue
    d = state.decision
    r["decision"] = None if d is None else [d.kind, d.resume, d.player, list(d.options)]
    r["invariants"] = check_invariants(state)
    for label, fn in (("export34", lambda: state_to_dict(state, format_version=34)), ("observe", lambda: observe(state, 0))):
        try:
            fn(); r[label] = "ok"
        except Exception as e:
            r[label] = err(e)
    before, rng_before, log_before = fp(state), rng_fingerprint(state.rng), len(state.log)
    answers = {}
    for choice in (case.get("choices") or []):
        try:
            new = apply_command(state, ResolveDecision(d.player, d.id, (choice,)))
            nd = new.decision
            answers[str(choice)] = {"accepted": True, "next": None if nd is None else [nd.kind, nd.player], "invariants": check_invariants(new)}
        except Exception as e:
            answers[str(choice)] = {"accepted": False, **err(e)}
    r["answers"] = answers
    r["unchanged_after_answers"] = [fp(state) == before, rng_fingerprint(state.rng) == rng_before, len(state.log) == log_before]
    out["cases"][name] = r
print(json.dumps(out, ensure_ascii=False))
'''


def _old_tree(workdir: pathlib.Path) -> pathlib.Path:
    """比べる旧版（v0.138）の ``kyuura_engine`` を ``git archive`` で読み取り用の木に取り出す（作業ツリー・履歴は変えない）。"""
    data = subprocess.run(["git", "-C", str(ROOT), "archive", OLD_COMMIT, "kyuura_engine"], check=True, capture_output=True).stdout
    tree = workdir / "old"
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tree, filter="data")
    return tree


def compat_states():
    """v0.139 で作る状態: 順番の決定を待つ（seed 473 の合法な操作の列）・サイドの決定を待つ（同じ列でロケット団参上!なし。v0.138 と同じ形）。"""
    from tests.test_prize_order_hc1_fix_v0_139 import legal_double_knockout
    return {"prize_order": (legal_double_knockout(), [0, 1, 2]), "take_prize": (legal_double_knockout(rocket=False), None)}


def _run_child(tree: pathlib.Path, payload: dict, workdir: pathlib.Path) -> dict:
    path = workdir / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"} | {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
    proc = subprocess.run([sys.executable, "-P", "-s", "-X", "utf8", "-c", COMPAT_CHILD, str(tree), str(path)], capture_output=True, text=True, encoding="utf-8", env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    return json.loads(proc.stdout)


def compat_evidence() -> dict:
    import kyuura_engine
    from kyuura_engine import state_to_dict
    from kyuura_engine.rng import rng_fingerprint
    states = compat_states()
    payload = {}
    current = {}
    for name, (state, choices) in states.items():
        d = state.decision
        if name == "take_prize":
            choices = list(d.options[:1])
        payload[name] = {"pickle": pickle.dumps(state).hex(), "choices": choices}
        exported = state_to_dict(state, format_version=34)
        current[name] = {"decision": [d.kind, d.resume, d.player, list(d.options)],
                         "export34_top_level_keys": sorted(exported),
                         "export34_decision": {k: exported["decision"][k] for k in ("kind", "resume", "player", "options")},
                         "export34_has_engine_version": any("version" in k and k != "format_version" for k in exported),
                         "export34_format_version": exported.get("format_version")}
        # 同じ版の中: 保存・復元して両方の答えで進められるか（順番の決定は 0・1 の両方）
        restored = pickle.loads(pickle.dumps(state))
        same = []
        for choice in (choices if name == "prize_order" else d.options[:1]):
            if choice not in d.options:
                continue
            a, b = _answer(state, choice), _answer(restored, choice)
            while a.decision is not None and a.decision.kind in ("take_prize", "prize_order"):
                a, b = _answer(a, a.decision.options[0]), _answer(b, b.decision.options[0])
            same.append([choice, state_to_dict(a, format_version=34) == state_to_dict(b, format_version=34), rng_fingerprint(a.rng) == rng_fingerprint(b.rng)])
        current[name]["restore_same_version"] = same
    current["unknown_resume"] = _unknown_resume(states["take_prize"][0])
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        old = _run_child(_old_tree(workdir), payload, workdir)
        new = _run_child(ROOT, payload, workdir)
        # 旧版で作った写しを今の版で読む（後方の互換）: 旧版の別のプロセスで状態を作り、写しを返す
        back = _old_pickle_to_new(workdir)
    return {"old_commit": OLD_COMMIT, "old_version_seen": old["engine_version"], "new_version": kyuura_engine.__version__,
            "current": current, "old_reads_new": old["cases"], "new_reads_new": new["cases"], "new_reads_old": back}


def _unknown_resume(state) -> dict:
    """今の版（v0.139）が、知らない再開先の決定を待つ状態（後の版の状態の写しを読んだ場合を、決定の種類・再開先だけを書きかえて作る）に答えを受けたときの結果。
    書きかえは比較用（このスクリプトの中だけ）。"""
    from dataclasses import replace

    from kyuura_engine import (
        EngineError,
        ResolveDecision,
        apply_command,
        check_invariants,
        state_to_dict,
    )
    from kyuura_engine.rng import rng_fingerprint
    fake = state.clone()
    fake.decision = replace(fake.decision, kind="future_decision", resume="future_decision")
    before = (_digest(state_to_dict(fake, format_version=34)), rng_fingerprint(fake.rng), len(fake.log))
    out = {"invariants": check_invariants(fake)}
    try:
        apply_command(fake, ResolveDecision(fake.decision.player, fake.decision.id, (fake.decision.options[0],)))
        out["answer"] = {"accepted": True}
    except (RuntimeError, EngineError) as e:  # 内部エラー・エンジンの拒否の種類を記録する（ほかの例外は捕まえない）
        out["answer"] = {"accepted": False, "type": type(e).__name__, "code": getattr(e, "code", None), "message": str(e)[:300]}
    out["unchanged"] = [before == (_digest(state_to_dict(fake, format_version=34)), rng_fingerprint(fake.rng), len(fake.log))]
    return out


OLD_MAKER = r'''
import json, pickle, sys, pathlib
tree = sys.argv[1]
sys.path.insert(0, tree)
import kyuura_engine
from kyuura_engine import new_game, expand_decklist, apply_command, AttachEnergy, EndTurn, UseAttack, DrawMulliganCards, ReportJankenResult, PlaceStartingPokemon
from kyuura_engine.state import Phase
DECK0 = {"PMCG1-036": 4, "PMCG4-062": 4, "PMCG1-100": 52}
DECK1 = {"PMCG1-060": 4, "PMCG1-099": 56}
state = new_game(expand_decklist(DECK0), expand_decklist(DECK1), 473)
print(json.dumps({"version": kyuura_engine.__version__, "pickle": pickle.dumps(state).hex()}))
'''


def _old_pickle_to_new(workdir: pathlib.Path) -> dict:
    """旧版（v0.138）の new_game(seed 473) の写しを今の版で読み、今の版の new_game と同じ書き出しになるか。"""
    from kyuura_engine import expand_decklist, new_game, state_to_dict
    tree = workdir / "old"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"} | {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
    proc = subprocess.run([sys.executable, "-P", "-s", "-X", "utf8", "-c", OLD_MAKER, str(tree)], capture_output=True, text=True, encoding="utf-8", env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    made = json.loads(proc.stdout)
    state = pickle.loads(bytes.fromhex(made["pickle"]))
    fresh = new_game(expand_decklist({"PMCG1-036": 4, "PMCG4-062": 4, "PMCG1-100": 52}), expand_decklist({"PMCG1-060": 4, "PMCG1-099": 56}), 473)
    exported = state_to_dict(state, format_version=34)
    expected = state_to_dict(fresh, format_version=34)
    return {"made_by": made["version"], "unpickle": "ok", "export34_equal_to_new_game": exported == expected}


# ---------------------------------------------------------------- 実行


def _require_recorded_engine() -> None:
    """記録を作ったエンジン（v0.139 の ``resolution.prize_order_matters`` がある）でなければ止める（今の動きで記録を作り直さない）。"""
    from kyuura_engine.resolution import flow
    if not hasattr(flow, "prize_order_matters"):
        raise SystemExit("このスクリプトは d631038 の木で動かす（今のエンジンは v0.140 で順番の決定を改めた。docs/prize-order-user-rule-v0.140.md 6 章）")


def evidence() -> dict:
    _require_recorded_engine()
    with contextlib.redirect_stdout(io.StringIO()):
        return {"knowledge": knowledge_evidence(), "units": units_evidence(), "compat": compat_evidence()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--print", action="store_true")
    args = parser.parse_args(argv)
    result = evidence()
    if args.print:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    if args.write:
        ledger["evidence"] = result
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{LEDGER.relative_to(ROOT).as_posix()} の evidence を書いた")
        return 0
    if ledger.get("evidence") != result:
        print("記録の evidence と今の再現が違う（scripts/prize_order_followup.py --print で確かめる）")
        return 1
    print("記録の evidence と今の再現が一致している")
    return 0


if __name__ == "__main__":
    sys.exit(main())
