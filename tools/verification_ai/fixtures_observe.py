"""主体別の観測の記録の限定確認の構築盤面と、ケースの選び手（検証者の側の固定の fixture。docs/verification-ai-observation.md 6 章）。

カード固有の準備（どのカードを使うか・何枚選ぶか）は、このモジュールに閉じ込めます（共通の行動生成・方策・判定・記録には入れない）。盤面は既存のテストの関数（``tests/``）で
作ります。作ったあとの操作は、本物の ``runner.Runner``（開始だけ fixture の状態。``FixtureRunner``）が公開の API（candidates・inputs・check・submit）で行います。
通常の new_game から届いた証拠とは扱いません。完全な再現用記録は作りません（``FixtureGame.close`` は None）。

ケースの選び手（``CasePicker``）は方策ではありません。ケースの条件に合う候補・選べるもの・枚数を、応答の公開の値（種類・カード id・場所・段の決定の種類）で選び、
条件に当たらない場面は均等の方策（``policies.UniformPolicy``）に任せます。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kyuura_engine import diagnostics as D
from kyuura_engine.adapter import HostedGame, checked_state_copy
from kyuura_engine.engine import check_invariants
from kyuura_engine.replay_record import checks

from .policies import STAGE, UniformPolicy
from .runner import ClientHub, Config, HOST, Limits, Runner

ROOT = Path(__file__).resolve().parents[2]
COMPUTER_SEARCH, POKEMON_TRADER, ENERGY_RETRIEVAL = "PMCG1-090", "PMCG1-093", "PMCG1-076"
CASE_LIMITS = Limits(operations=40, accepted=20, turns=4, seconds=60.0)


def _sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# ---------------------------------------------------------------- 盤面（出典のテストの関数そのまま）


def _computer_search():
    from tests import test_computer_search_v0_22 as T

    return T.board()


def _pokemon_trader():
    from tests import test_pokemon_trader_v0_24 as T

    return T.board()


def _energy_retrieval():
    from tests import test_energy_retrieval_v0_23 as T

    return T.board()


def _muk_decision():
    from kyuura_engine import CoinSide, UseAttack, apply_command
    from tests import helpers as H
    from tests import test_final_pmcg_cards_v0_68 as T68

    return apply_command(H.with_coin_results(T68.muk_board(), CoinSide.HEADS), UseAttack(0, 0))


def _p6a():
    from . import fixtures_p6

    return fixtures_p6.build("P6A")[0]


def _ur3a_rc():
    from . import fixtures_u_r3a

    return fixtures_u_r3a.build("UR3A-RC")[0]


FIXTURES: dict[str, dict[str, Any]] = {
    "O-SEARCH": {"build": _computer_search, "source": [("tests/test_computer_search_v0_22.py", "board()（既定の引数。プレイヤー 0 の番の MAIN・手札の先頭がパソコン通信）")]},
    "O-TRADER": {"build": _pokemon_trader, "source": [("tests/test_pokemon_trader_v0_24.py", "board()（既定の引数。手札の先頭がポケモン交換おじさん）")]},
    "O-ER9": {"build": _energy_retrieval, "source": [("tests/test_energy_retrieval_v0_23.py", "board()（既定の引数。手札の先頭がエネルギー回収・トラッシュに基本エネルギー 3 枚）")]},
    "O-OPPONENT": {"build": _muk_decision, "source": [("tests/test_legal_actions_u7_1.py", "CoverageTest.test_decision_answerer_has_priority_over_the_turn"),
                                                      ("tests/test_final_pmcg_cards_v0_68.py", "muk_board()・with_coin_results(HEADS)・UseAttack(0, 0)（プレイヤー 1 が答える決定）")]},
    "O-P6A": {"build": _p6a, "source": [("tools/verification_ai/fixtures_p6.py", "build('P6A')"),
                                        ("tests/test_legal_actions_p6_face_down_retreat_v0_174.py", "face_down_active")]},
    "O-UR3A": {"build": _ur3a_rc, "source": [("tools/verification_ai/fixtures_u_r3a.py", "build('UR3A-RC')"),
                                             ("tests/test_legal_actions_u_r3a_v0_175.py", "placed")]},
}


def build(fixture_id: str):
    """(状態, 記録)。記録は出典（ファイルの sha256）・整合の確かめ。本当のカードを含むことがあるので verifier の側だけに保存する。"""
    spec = FIXTURES[fixture_id]
    state = spec["build"]()
    record = {"fixture": fixture_id, "origin": "constructed_fixture", "new_game": False,
              "source": [{"file": f, "what": w, "sha256": _sha256(f)} for f, w in spec["source"]],
              "integrity": {"check_invariants": check_invariants(state), "state_usable": D.state_usable(state), "status": D.status_of(state),
                            "phase": state.phase.value, "turn": state.turn_number, "current_player": state.current_player}}
    return state, record


# ---------------------------------------------------------------- 本物の runner を fixture の状態から始める


class FixtureGame:
    """fixture の状態（の確かめた複製）を包むホストの対戦（``HostedGame``）。runner が使う ``state``・``submit``・``failure``・``last_check``・``close`` だけを持つ。
    完全な再現用記録は作らない（close は None）。"""

    def __init__(self, state):
        self._game = HostedGame(checked_state_copy(state))
        self._check = checks(self._game.state)

    @property
    def state(self):
        return self._game.state

    @property
    def failure(self):
        return self._game.failure

    def submit(self, command, *, submitter=None, operation_id=None):
        result = self._game.submit(command, submitter=submitter, operation_id=operation_id)
        if result.outcome == D.ACCEPTED:
            self._check = checks(self._game.state)
        return result

    def last_check(self):
        return self._check

    def close(self):
        return None


class FixtureRunner(Runner):
    """開始だけを fixture の状態にした ``Runner``（進行・照合・記録・更新の取り出しは Runner のまま）。"""

    def __init__(self, state, config: Config, **kwargs):
        super().__init__(config, **kwargs)
        self._fixture_state = state

    def _start(self) -> None:
        self.game = FixtureGame(self._fixture_state)
        self.hub = ClientHub(self.game, verifier=self._on_verifier)
        self.endpoints = {0: self.wrap_endpoint(0, self.hub.player(0)), 1: self.wrap_endpoint(1, self.hub.player(1)), HOST: self.wrap_endpoint(HOST, self.hub.host())}
        self._rec("start", self.game.state)


# ---------------------------------------------------------------- ケースの選び手（方策ではない）


class CasePicker(UniformPolicy):
    """ケースの条件に合う場面だけ ``pick`` で選び、ほかは均等（UniformPolicy と同じ乱数・同じ数え方）。"""

    name = "case-picker"

    def __init__(self, seed: str, pick):
        super().__init__(seed, STAGE)
        self._pick = pick

    def choose(self, purpose, items, context):
        index = self._pick(purpose, items, context)
        if index is None:
            return super().choose(purpose, items, context)
        return index, f"case:{purpose}"


def _option(item, context) -> dict[str, Any]:
    """行動生成が渡す選べるものの番号から、段の選べるものの中身（公開の値）を引く。"""
    stage = context.get("stage") or {}
    for o in stage.get("options", []):
        if o.get("id") == item:
            return o
    return {}


def _prefer_card(card_id):
    """決定への回答があればそれ、なければトレーナーを使う候補で、手札の ``card_id`` を選ぶ。ほかの枚数・選べるものは均等。"""

    def pick(purpose, items, context):
        if purpose == "candidate":
            for kind in ("answer_decision", "play_trainer"):
                for i, c in enumerate(items):
                    if c["kind"] == kind:
                        return i
            return None
        if purpose == "option" and (context.get("candidate") or {}).get("kind") == "play_trainer":
            for i, item in enumerate(items):
                if _option(item, context).get("card_id") == card_id:
                    return i
        return None

    return pick


def _er9_pick():
    """エネルギー回収: 回収の段で、最初は 0 枚（ER9 の拒否の条件をケースが知っている）、拒否のあとは 1 枚。"""
    state = {"zero_used": False}
    base = _prefer_card(ENERGY_RETRIEVAL)

    def pick(purpose, items, context):
        if purpose == "candidate":
            return base(purpose, items, context)
        stage = context.get("stage") or {}
        if purpose == "count" and stage.get("decision_kind") == "retrieve_energy":
            want = 0 if not state["zero_used"] else 1
            state["zero_used"] = True
            return items.index(want) if want in items else None
        return None

    return pick


def _answer_first(purpose, items, context):
    if purpose == "candidate":
        for i, c in enumerate(items):
            if c["kind"] == "answer_decision":
                return i
    return None


def _p6_pick(purpose, items, context):
    """P6A: うらのバトル場のにげる。エネルギーをトラッシュしない（0 枚。受理される条件をケースが知っている）。"""
    if purpose == "candidate":
        for i, c in enumerate(items):
            if c["kind"] == "retreat":
                return i
        return _answer_first(purpose, items, context)
    if purpose == "count":
        return items.index(0) if 0 in items else None
    return None


def _ur3a_pick(purpose, items, context):
    """UR3A-RC: うらのロケット団のヒトカゲの特殊能力。ベンチのコラッタ → 炎エネルギー（受理される条件をケースが知っている。fixtures_u_r3a.rattata_fire と同じ組）。"""
    from . import fixtures_u_r3a as U
    from .judge import is_face_down_power

    if purpose == "candidate":
        for i, c in enumerate(items):
            if is_face_down_power(c):
                return i
        return _answer_first(purpose, items, context)
    if purpose == "option":
        for i, item in enumerate(items):
            o = _option(item, context)
            if (o.get("zone") == "bench" and o.get("card_id") == U.RATTATA) or (o.get("card_id") == U.FIRE and o.get("zone") != "bench"):
                return i
    return None


def _after_stage(kind):
    def until(runner, entry):
        return any(s.get("decision_kind") == kind for s in entry.get("stages") or [])

    return until


def _after_actor(actor):
    def until(runner, entry):
        return entry["actor"] == actor

    return until


def _after_kind(kind):
    def until(runner, entry):
        return entry["candidate"]["kind"] == kind

    return until


CASES: dict[str, dict[str, Any]] = {
    "search": {"fixture": "O-SEARCH", "pick": lambda: _prefer_card(COMPUTER_SEARCH), "until": _after_stage("search_deck"),
               "purpose": "パソコン通信: 回答者だけが山札の選べるものを見る。相手・観戦者に山札の中身・選んだカードが出ない"},
    "trader": {"fixture": "O-TRADER", "pick": lambda: _prefer_card(POKEMON_TRADER), "until": _after_stage("search_deck"),
               "purpose": "ポケモン交換おじさん: もどしたカード・選んだカードが全員のログに出る"},
    "opponent": {"fixture": "O-OPPONENT", "pick": lambda: _answer_first, "until": _after_actor(1),
                 "purpose": "相手（プレイヤー 1）が答える決定: 入力は答える主体だけに届く"},
    "er9": {"fixture": "O-ER9", "pick": _er9_pick, "until": _after_stage("retrieve_energy"),
            "purpose": "エネルギー回収の 0 枚の拒否（ER9）: 本人だけに診断。他者への新しい更新・ログがない。選び直しが受理される"},
    "p6": {"fixture": "O-P6A", "pick": lambda: _p6_pick, "until": _after_kind("retreat"), "profile": "boundary",
           "purpose": "P6A: うらのバトル場のにげるの受理。公開のログが受理の中身の判定へ渡る"},
    "ur3a": {"fixture": "O-UR3A", "pick": lambda: _ur3a_pick, "until": _after_kind("use_power"), "profile": "boundary",
             "purpose": "UR3A-RC: うらのカードの特殊能力の受理。公開のログが受理の中身の判定へ渡る"},
}


def run_case(name: str, *, recorder=None, limits: Limits = CASE_LIMITS) -> dict[str, Any]:
    """ケースを本物の runner で 1 回実行し、runner の結果（と fixture の記録）を返す。"""
    spec = CASES[name]
    state, record = build(spec["fixture"])
    seed = f"kyuura-vai-observe:{name}"
    # P6・U-R3a のうらのカードの送信は処理可能性 unverified なので、範囲に unverified を入れるプロファイル boundary（V3-2 と同じ。表示だけ・実行できない区分は外したまま）
    config = Config(run_id=f"observe-{name}", limits=limits, profile=spec.get("profile", "deep"))
    runner = FixtureRunner(state, config, policy_factory=lambda s, d: CasePicker(f"{seed}:{s}", spec["pick"]()), until=spec["until"], recorder=recorder)
    result = runner.run()
    result["fixture"] = record
    result["case"] = {"name": name, "purpose": spec["purpose"]}
    result["final_state"] = runner.game.state if runner.game is not None else None
    return result
