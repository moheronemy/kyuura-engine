"""ヘッドレスの参照クライアント（v0.164。docs/client-api-v0.164.md の接続の確かめ）。

GUI の代わりに、クライアント向けのアダプタ（``kyuura_engine.client_api``）の入口だけを使って対戦を進める。使うのは JSON の要求・応答（許された観測・候補・入力の制約・
定型の診断）だけで、``GameState``・実際の山札・相手の手札・完全な記録・スナップショット・検証者用の診断を読まない（入口の ``handle`` に dict を渡し、dict を受け取るだけ）。

入口を作って配るのは信頼されたホストの側（``main`` の最初の数行）。このクライアントの関数は入口を受け取るだけで、hub・対戦に触れない。

今の U7 の範囲（決定への回答・番を終える・準備・ホストの操作）では、ワザ・トレーナーなどを選べないので、勝つための方策は作れない。番を終えるだけで進めると、山札が
なくなって終局する（参照クライアントの到達範囲）。

    python examples/headless_client.py   # リポジトリの根で
"""

from __future__ import annotations

import json
import sys

CONTRACT = {"contract": "kyuura-client-api", "format": 1}


def request(endpoint, kind, **fields) -> dict:
    """要求を JSON にして送り、応答を JSON にして受け取る（通信の代わりに文字列を通す）。"""
    text = json.dumps({**CONTRACT, "type": kind, **fields}, ensure_ascii=False)
    answer = endpoint.handle(json.loads(text))
    return json.loads(json.dumps(answer, ensure_ascii=False))


def choose(kind: str, stages: list) -> list | None:
    """候補の入力の制約だけから選ぶ（決まった選び方）。選べなければ None。"""
    if not stages:
        return []
    stage = stages[0]
    if stage["input"] == "choose_value":
        if kind == "mulligan_draw":
            return [stage["range"]["max"]]
        return [stage["range"]["min"]]
    if kind == "place_starting":
        eligible = [o["id"] for o in stage["options"] if o.get("eligible")]
        return eligible[:3] or None
    usable = [o["id"] for o in stage["options"] if o.get("processability") in ("supported", "may_stop_later", "unverified")]
    need = stage["count"]["min"]
    return usable[:need] if len(usable) >= need else None


def act(endpoint, trace: list) -> bool:
    """入口の候補を 1 つ選んで送る。送れたら True。"""
    answer = request(endpoint, "candidates")
    response = answer["response"]
    if not response["candidates"]:
        return False
    cand = response["candidates"][0]
    inputs = request(endpoint, "inputs", game=response["game"], revision=response["revision"], candidate=cand["id"])
    if not inputs["ok"] or "withheld" in inputs["response"]:
        trace.append({"stop": "input_not_available", "kind": cand["kind"]})
        return False
    choices = choose(cand["kind"], inputs["response"]["stages"])
    if choices is None:
        trace.append({"stop": "no_choice", "kind": cand["kind"]})
        return False
    result = request(endpoint, "submit", game=response["game"], revision=response["revision"], candidate=cand["id"], choices=choices)
    trace.append({"actor": response["actor"], "kind": cand["kind"], "outcome": result["outcome"], "refetch_required": result["refetch_required"]})
    return result["outcome"] == "accepted"


def play(players: dict, host, spectator, *, max_steps: int = 2000) -> dict:
    """入口だけで進める。だれにも候補がない・終局・停止・延長戦の開始の待ち（ホストが始める）まで。"""
    trace: list = []
    seen = []
    for _ in range(max_steps):
        status = request(spectator, "view")["status"]
        seen.append(status["status"])
        if status["status"] in ("game_over", "halted"):
            break
        if any(act(p, trace) for p in players.values()):
            continue
        if act(host, trace):
            continue
        break
    updates = {str(audience): request(endpoint, "updates")["updates"] for audience, endpoint in (*players.items(), ("spectator", spectator))}
    return {"final": request(spectator, "view")["status"], "trace": trace, "statuses": seen, "updates": updates}


def main() -> int:
    # ここから 4 行は信頼されたホストの側（入口を作って配る）
    sys.path.insert(0, ".")
    from kyuura_engine.client_api import ClientHub
    from kyuura_engine.decks import PRESET_DECKS

    decks = list(PRESET_DECKS.values())[:2]
    hub, notice = ClientHub.start(decks[0].cards(), decks[1].cards(), 0)
    if hub is None:
        print(json.dumps(notice, ensure_ascii=False))
        return 1
    report = play({0: hub.player(0), 1: hub.player(1)}, hub.host(), hub.spectator())
    print(json.dumps({"final": report["final"], "steps": len(report["trace"]), "last": report["trace"][-3:]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
