"""通常のインストール（wheel・Git の URL）で入れた kyuura_engine の小さな確かめ（v0.164 の配布の修正。docs/installation.md）。

    <仮想環境>/python <このファイル>        # リポジトリの外を作業ディレクトリにして実行する

- ソースの木を読み込まない（``sys.path`` を変えない。読み込んだ ``kyuura_engine`` が site-packages の下になければ止める）
- 公開の API だけを使う: 全サブパッケージの読み込み・版・同梱のカードデータと登録データ・規約集合の識別・``new_game``・``ClientHub`` の開始と
  本人・相手・観戦者・ホストの入口・初期配置の操作・ホストのジャンケンの結果・番の基本の操作（v0.165。U7-3）・記録と保存の部品の読み込み・実装の識別
- 結果を JSON で出す（``implementation_identity`` をソースの木の値と比べるのは呼ぶ側）。問題があれば終了コード 1
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import pathlib
import pkgutil
import sys

# 名前で必ず読み込むモジュール（v0.164 の配布物では resolution が欠けていた）
REQUIRED_MODULES = (
    "kyuura_engine.engine", "kyuura_engine.client_api", "kyuura_engine.legal_actions", "kyuura_engine.adapter", "kyuura_engine.diagnostics",
    "kyuura_engine.observation", "kyuura_engine.resolution", "kyuura_engine.resolution.kernel", "kyuura_engine.resolution.preflight",
    "kyuura_engine.replay_record", "kyuura_engine.replay_run", "kyuura_engine.view_record", "kyuura_engine.snapshot", "kyuura_engine.snapshot_replay",
)
CONVENTION_SETS = (("CS-KYUURA-CURRENT", 1), ("CS-KYUURA-PLAY-S2A", 1), ("CS-KYUURA-PLAY-PO", 1))
CONTRACT = {"contract": "kyuura-client-api", "format": 1}


def check(problems: list[str], condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


def placement_choices(stages: list) -> list:
    eligible = [o["id"] for o in stages[0]["options"] if o.get("eligible")]
    return eligible[:1]


TURN_KINDS = ("play_basic", "attach_energy", "evolve", "retreat")


def request(endpoint, kind: str, **fields) -> dict:
    return endpoint.handle({**CONTRACT, "type": kind, **fields})


def turn_action_choices(kind: str, stages: list) -> list | None:
    """番の基本の操作の入力（候補の制約だけから。1 段目の eligible → 2 段目は options_by_choice の eligible。にげるは個数の下限まで）。"""
    first = next((o for o in stages[0]["options"] if o.get("eligible")), None)
    if first is None:
        return None
    if kind == "play_basic":
        return [first["id"]]
    if kind == "retreat":
        choices, units = [first["id"]], 0
        for option in stages[1]["options"]:
            if units >= stages[1]["total_units"]["min"]:
                break
            choices.append(option["id"])
            units += option["units"]
        return choices
    pair = next((p for p in stages[1]["options_by_choice"][first["id"]] if p["eligible"]), None)
    return None if pair is None else [first["id"], pair["option"]]


def to_first_turn(endpoints) -> None:
    """準備の残り（補償の引く枚数）を候補だけで進め、ホストの入口でジャンケンの結果（プレイヤー 0 が先攻）を送る。"""
    for _ in range(20):
        for name in ("0", "1"):
            answer = request(endpoints[name], "candidates")["response"]
            for cand in answer["candidates"]:
                if cand["kind"] == "mulligan_draw":
                    fields = {"game": answer["game"], "revision": answer["revision"], "candidate": cand["id"]}
                    stage = request(endpoints[name], "inputs", **fields)["response"]["stages"][0]
                    request(endpoints[name], "submit", **fields, choices=[stage["range"]["max"]])
    answer = request(endpoints["host"], "candidates")["response"]
    for cand in answer["candidates"]:
        if cand["kind"] == "report_janken":
            request(endpoints["host"], "submit", game=answer["game"], revision=answer["revision"], candidate=cand["id"], choices=[0])


def main() -> int:
    problems: list[str] = []
    import kyuura_engine

    location = pathlib.Path(kyuura_engine.__file__).resolve()
    if "site-packages" not in location.parts:
        print(json.dumps({"problems": [f"kyuura_engine をインストール先から読み込んでいない: {location}"]}, ensure_ascii=False))
        return 1
    report: dict = {"location": str(location.parent), "python": list(sys.version_info[:3])}

    for name in REQUIRED_MODULES:
        importlib.import_module(name)
    walked = sorted(m.name for m in pkgutil.walk_packages(kyuura_engine.__path__, "kyuura_engine."))
    for name in walked:
        importlib.import_module(name)
    report["modules"] = len(walked)
    check(problems, "kyuura_engine.resolution.kernel" in walked, "resolution.kernel が見つからない")

    report["version"] = kyuura_engine.__version__
    check(problems, importlib.metadata.version("kyuura-engine") == kyuura_engine.__version__, "配布物の版と __version__ が違う")

    from kyuura_engine import conventions, diagnostics, heights, replay_record
    from kyuura_engine.cards import load_card_pool
    from kyuura_engine.client_api import ClientHub
    from kyuura_engine.decks import PRESET_DECKS
    from kyuura_engine.engine import new_game

    pool = load_card_pool()
    decks = list(PRESET_DECKS.values())[:2]
    deck0, deck1 = decks[0].cards(), decks[1].cards()
    check(problems, all(card in pool.definitions for card in deck0 + deck1), "固定デッキのカードが同梱のカードデータにない")
    report["cards"] = len(pool.definitions)
    report["behavior_records"] = len(conventions.current_behavior_records())
    report["diagnostic_catalog"] = diagnostics.default_catalog() is not None
    report["species_heights"] = heights.load_species_heights() is not None
    report["convention_sets"] = {f"{key[0]}@{key[1]}": conventions.registered_identity(key).digest for key in CONVENTION_SETS}
    for key, digest in report["convention_sets"].items():
        set_id, version = key.split("@")
        check(problems, digest == conventions.PINNED_SET_DIGESTS[(set_id, int(version))], f"{key} の照合値が固定の値と違う")

    state = new_game(deck0, deck1, 0)
    report["new_game_phase"] = state.phase.name

    hub, notice = ClientHub.start(deck0, deck1, 0)
    check(problems, hub is not None and notice.get("ok") is True, "ClientHub.start が始まらない")
    if hub is not None:
        endpoints = {"0": hub.player(0), "1": hub.player(1), "spectator": hub.spectator(), "host": hub.host()}
        views = {name: e.handle({**CONTRACT, "type": "view"}) for name, e in endpoints.items()}
        check(problems, all(v["ok"] for v in views.values()), "view に失敗した")
        report["view_status"] = views["spectator"]["status"]["status"]
        refused = endpoints["spectator"].handle({**CONTRACT, "type": "candidates"})
        check(problems, refused.get("error", {}).get("code") == "CLIENT_REQUEST_UNKNOWN", "観戦者の候補の要求が拒否されない")
        placed = []
        for name in ("0", "1"):
            answer = endpoints[name].handle({**CONTRACT, "type": "candidates"})["response"]
            kinds = [c["kind"] for c in answer["candidates"]]
            check(problems, "place_starting" in kinds, f"本人 {name} に初期配置の候補がない")
            if "place_starting" not in kinds:
                continue
            cand = answer["candidates"][kinds.index("place_starting")]
            fields = {"game": answer["game"], "revision": answer["revision"], "candidate": cand["id"]}
            inputs = endpoints[name].handle({**CONTRACT, "type": "inputs", **fields})
            result = endpoints[name].handle({**CONTRACT, "type": "submit", **fields, "choices": placement_choices(inputs["response"]["stages"])})
            placed.append(result["outcome"])
        report["placements"] = placed
        check(problems, placed == ["accepted", "accepted"], "初期配置が受理されない")
        numbers = {name: [u["number"] for u in endpoints[name].handle({**CONTRACT, "type": "updates"})["updates"]] for name in ("0", "1", "spectator")}
        report["update_numbers"] = numbers
        check(problems, all(n == [1, 2] for n in numbers.values()), "閲覧者ごとの公開の更新が受理の数と合わない")
        to_first_turn(endpoints)
        answer = request(endpoints["0"], "candidates")["response"]
        offered = [c["kind"] for c in answer["candidates"]]
        report["turn_offered"] = offered
        check(problems, "end_turn" in offered and any(kind in offered for kind in TURN_KINDS), "番の基本の操作の候補がない")
        sent = None
        for cand in answer["candidates"]:
            if cand["kind"] in TURN_KINDS and cand["processability"] in ("supported", "may_stop_later", "unverified"):
                fields = {"game": answer["game"], "revision": answer["revision"], "candidate": cand["id"]}
                choices = turn_action_choices(cand["kind"], request(endpoints["0"], "inputs", **fields)["response"]["stages"])
                if choices is not None and request(endpoints["0"], "check", **fields, choices=choices)["response"]["valid"]:
                    sent = (cand["kind"], request(endpoints["0"], "submit", **fields, choices=choices)["outcome"])
                    break
        report["turn_action"] = sent
        check(problems, sent is not None and sent[1] == "accepted", "番の基本の操作が受理されない")

    report["implementation_identity"] = replay_record.implementation_identity()
    report["problems"] = problems
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
