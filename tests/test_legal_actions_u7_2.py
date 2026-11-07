"""v0.163（U7-2。docs/legal-actions-u7-2.md）: 準備の操作（初期配置・切り直しの補償の引く枚数）とホストの操作（ジャンケンの結果・延長戦の開始）の回帰テスト。

確かめの種類を分ける:

- new_game からの合法な操作の列: U7 だけで準備を終えて番に進む（直接の送信と同じ状態・乱数・ログ・観測・診断）、3 つの規約集合の化石の扱い、延長戦の開始と準備
- 構築盤面（状態の写しの規則・山札の並びを変える）: ベンチの上限、双子
- 補助の作り（アダプタの内部エラーを差し替える）: 処理できない結果のあとの停止

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.commands import (
    DrawMulliganCards,
    PlaceStartingPokemon,
    ReportJankenResult,
    StartSuddenDeath,
)
from kyuura_engine.conventions import continuation_for
from kyuura_engine.engine import SETUP_PLACEMENT_CASE, new_game
from kyuura_engine.observation import observe
from kyuura_engine.state import Phase
from tests import helpers as H
from tests import test_sudden_death_v0_134 as SD
from tests.log_audit import owned_card_ids, public_view
from tests.test_legal_actions_u7_1 import fetch, snap, without_handles

BABY = "neo1-022"
MULLIGAN_DECKS = ([H.PIKACHU] + [H.FIRE] * 59, [H.PIKACHU] * 4 + [H.FIRE] * 56)  # seed 0: プレイヤー 1 に補償 7 回
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")


def full_snap(state):
    return snap(state), tuple(json.dumps(observe(state, v), sort_keys=True, default=repr) for v in (0, 1, None))


def first_seed(decks, predicate, *, conventions=None, limit=60):
    options = {} if conventions is None else {"conventions": conventions}
    for seed in range(limit):
        state = new_game(*decks, seed, **options)
        if predicate(state):
            return seed
    raise AssertionError("条件に合う seed がない")


def choose(session):
    """U7 の候補だけから選ぶ方策: 初期配置は選べるもの（eligible）を手札の順に最大 3 枚、補償は上限の枚数。"""
    r, inputs = fetch(session)
    cand = r["candidates"][0]
    stage = inputs["stages"][0]
    if cand["kind"] == L.KIND_PLACE_STARTING:
        return r, cand, [o["id"] for o in stage["options"] if o["eligible"]][:3]
    if cand["kind"] in (L.KIND_MULLIGAN_DRAW, L.KIND_REPORT_JANKEN):
        return r, cand, [stage["range"]["max"] if cand["kind"] == L.KIND_MULLIGAN_DRAW else 0]
    raise AssertionError(cand["kind"])


def setup_via_u7(test, host):
    """U7 の入口だけで準備を終える。送ったコマンドを、同じ状態に直接送った結果と比べる。"""
    hs = host.host_session()
    for _ in range(40):
        state = host.game.state
        if state.phase is not Phase.SETUP_PLACEMENT and state.phase is not Phase.SETUP_MULLIGAN_DRAW and state.phase is not Phase.SETUP_FIRST_PLAYER:
            return
        sessions = [host.session(a) for a in (0, 1)] + [hs]
        for session in sessions:
            r = session.candidates()
            if r["candidates"]:
                break
        else:
            raise AssertionError("準備で、だれにも候補がない")
        r, cand, choices = choose(session)
        found = host._issued[r["revision"]].candidates[cand["id"]]
        _, values = L._input_problem(found, choices)
        command = L._command(found, session.actor, values)
        direct = A.submit(state, command, submitter=None if session.actor == L.HOST else session.actor)
        result = session.submit(r["game"], r["revision"], cand["id"], choices)
        test.assertEqual(result.outcome, D.ACCEPTED)
        test.assertEqual(result.view, direct.view_for(None if session.actor == L.HOST else session.actor))
        test.assertEqual(full_snap(host.game.state), full_snap(direct.state))
    raise AssertionError("準備が終わらない")


class SetupFlowTest(unittest.TestCase):
    def test_new_game_to_the_turn_with_u7_only(self):
        host, start = L.ActionHost.start(*MULLIGAN_DECKS, 0)
        self.assertEqual(start.outcome, D.ACCEPTED)
        self.assertEqual([p.mulligan_draws_remaining for p in host.game.state.players], [0, 7])
        setup_via_u7(self, host)
        state = host.game.state
        self.assertEqual(state.phase, Phase.MAIN)
        r = host.session(state.current_player).candidates()
        self.assertEqual(r["candidates"][0]["kind"], L.KIND_END_TURN)  # U7-1 の番を終える候補へつながる
        self.assertEqual(host.host_session().candidates()["empty_reason"], L.EMPTY_PLAYERS_TO_ACT)

    def test_three_convention_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                host, _ = L.ActionHost.start(*MULLIGAN_DECKS, 0, **options)
                setup_via_u7(self, host)
                self.assertEqual(host.game.state.phase, Phase.MAIN)

    def test_setup_halted_at_start(self):
        host, _ = L.ActionHost.start(*MULLIGAN_DECKS, 1)  # 切り直しの補償で止まる準備（通常の準備と同じ停止）
        self.assertEqual(host.game.state.phase, Phase.HALTED)
        for session in (host.session(0), host.session(1), host.host_session()):
            r = session.candidates()
            self.assertEqual((r["situation"], r["candidates"], r["empty_reason"]), (L.HALTED, [], L.EMPTY_GAME_ENDED))


class PlacementTest(unittest.TestCase):
    def host(self, decks=([BABY] * 4 + [H.PIKACHU] * 4 + [H.FIRE] * 52,) * 2, **options):
        seed = first_seed(decks, lambda s: s.phase is Phase.SETUP_PLACEMENT and len([u for u in s.players[0].hand if s.card_def(u).is_baby_or_basic_pokemon]) >= 3,
                          **options)
        return L.ActionHost.start(*decks, seed, **({} if not options else {"conventions": options["conventions"]}))[0]

    def test_basic_and_baby_and_constraints(self):
        host = self.host()
        state = host.game.state
        p0 = host.session(0)
        r, inputs = fetch(p0)
        active, bench = inputs["stages"]
        self.assertEqual((active["role"], active["count"], bench["role"], bench["count"]["max"], bench["order"]),
                         ("active", {"min": 1, "max": 1}, "bench", state.rules.max_setup_bench, L.ORDER_SIGNIFICANT))
        hand = state.players[0].hand
        self.assertEqual([o["card"] for o in active["options"]], [u for u in hand if state.card_def(u).is_baby_or_basic_pokemon])
        self.assertTrue(any(state.card_def(o["card"]).is_baby_pokemon for o in active["options"]) or not any(state.card_def(u).is_baby_pokemon for u in hand))
        args = (r["game"], r["revision"], "c1")
        for bad in ([], ["o1", "o1"], ["o9"], ["x"], "o1", [1]):
            with self.subTest(bad=bad):
                self.assertEqual(p0.check(*args, bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertTrue(p0.check(*args, ["o1", "o2"])["valid"])
        r1 = host.session(1).candidates()  # 相手も同時に置ける（相手の候補には本人の手札がない）
        self.assertEqual(r1["candidates"][0]["kind"], L.KIND_PLACE_STARTING)
        self.assertEqual(p0.submit(r1["game"], r1["revision"], "c1", ["o1"]).refusal.code, L.CANDIDATES_WRONG_ACTOR)
        text = json.dumps(host.session(1).inputs(r1["game"], r1["revision"], "c1"))
        for uid in hand:
            self.assertNotIn(f'"card": {uid},', text)

    def test_bench_order_and_limit(self):
        host = self.host()
        finals = []
        for ids in (["o1", "o2", "o3"], ["o1", "o3", "o2"]):
            twin = L.ActionHost.from_state(host.game.state)
            s = twin.session(0)
            r = s.candidates()
            direct = A.submit(twin.game.state, L._command(twin._issued[r["revision"]].candidates["c1"], 0,
                                                          L._input_problem(twin._issued[r["revision"]].candidates["c1"], ids)[1]), submitter=0)
            self.assertEqual(s.submit(r["game"], r["revision"], "c1", ids).outcome, D.ACCEPTED)
            self.assertEqual(full_snap(twin.game.state), full_snap(direct.state))
            finals.append([p.card for p in twin.game.state.players[0].bench])
        self.assertEqual(finals[0], finals[1][::-1])  # ベンチは選んだ順に場に並ぶ（並びに意味がある）
        self.assertNotEqual(finals[0], finals[1])
        small = host.game.state.clone()
        small.rules = dataclasses.replace(small.rules, max_setup_bench=1)  # 構築: ベンチの上限を 1 に
        twin = L.ActionHost.from_state(small)
        r, inputs = fetch(twin.session(0))
        self.assertEqual(inputs["stages"][1]["count"]["max"], 1)
        self.assertEqual(twin.session(0).check(r["game"], r["revision"], "c1", ["o1", "o2", "o3"])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        direct = A.submit(small, PlaceStartingPokemon(0, inputs["stages"][0]["options"][0]["card"],
                                                       tuple(o["card"] for o in inputs["stages"][0]["options"][1:3])), submitter=0)
        self.assertEqual(direct.outcome, D.REJECTED)  # エンジンも同じ上限で拒否する（U7 は同じ値を使う）

    def test_fossil_in_three_convention_sets(self):
        decks = ([H.MYSTERIOUS_FOSSIL] * 4 + [H.PIKACHU] * 4 + [H.FIRE] * 52,) * 2
        seen = set()
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                seed = first_seed(decks, lambda s: s.phase is Phase.SETUP_PLACEMENT and E.play_as_pokemon_in_hand(s, 0)
                                  and any(s.card_def(u).is_basic_pokemon for u in s.players[0].hand), **options)
                host = L.ActionHost.start(*decks, seed, **options)[0]
                state = host.game.state
                p0 = host.session(0)
                r, inputs = fetch(p0)
                options_ = inputs["stages"][0]["options"]
                fossils = [o for o in options_ if o["card"] in E.play_as_pokemon_in_hand(state, 0)]
                self.assertTrue(fossils)  # 候補から消さない
                lookup = continuation_for(state, E.PLAY_AS_POKEMON_SETUP_CODE, SETUP_PLACEMENT_CASE)  # 状態の規約集合の続行規約（モードの名前で分けない）
                seen.add(lookup is None)
                for o in fossils:
                    self.assertFalse(o["eligible"])
                    if lookup is not None:
                        self.assertEqual(o["placement"], L.PLACEMENT_EXCLUDED_BY_CONVENTION)  # 続行規約による拒否（ゲーム上の未裁定ではない）
                        self.assertEqual(o["convention"], f"{lookup.convention[0]}@{lookup.convention[1]}")
                    else:
                        self.assertEqual((o["placement"], o["processability"]), (L.PLACEMENT_STOP, L.RULING_UNRESOLVED))
                self.assertEqual(r["candidates"][0]["processability"], L.SUPPORTED)  # たねポケモンがあるので配置はできる
                before = snap(state)
                result = p0.submit(r["game"], r["revision"], "c1", [fossils[0]["id"]])
                self.assertEqual(result.refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
                self.assertEqual(snap(host.game.state), before)
                direct = A.submit(state, PlaceStartingPokemon(0, fossils[0]["card"]), submitter=0)
                self.assertEqual(direct.outcome, D.REJECTED)  # エンジンも受け付けない（理由はエンジンの診断。U7 は送らない）
                eligible = next(o["id"] for o in options_ if o["eligible"])
                self.assertEqual(p0.submit(r["game"], r["revision"], "c1", [eligible]).outcome, D.ACCEPTED)
        self.assertEqual(seen, {True, False})  # 続行規約のある集合とない集合の両方を確かめた


class MulliganTest(unittest.TestCase):
    def host(self):
        host, _ = L.ActionHost.start(*MULLIGAN_DECKS, 0)
        for a in (0, 1):
            s = host.session(a)
            r, _, ids = choose(s)
            self.assertEqual(s.submit(r["game"], r["revision"], "c1", ids).outcome, D.ACCEPTED)
        self.assertEqual(host.game.state.phase, Phase.SETUP_MULLIGAN_DRAW)
        return host

    def test_counts_and_who_draws(self):
        host = self.host()
        state = host.game.state
        p0, p1 = host.session(0), host.session(1)
        r0 = p0.candidates()
        self.assertEqual((r0["situation"], r0["empty_reason"]), (L.WAITING_FOR_PLAYER, L.EMPTY_NOT_ACTOR))  # 補償を受けるのはプレイヤー 1 だけ
        r, inputs = fetch(p1)
        stage = inputs["stages"][0]
        top = min(state.rules.mulligan_draw_max_per_mulligan, len(state.players[1].deck))
        self.assertEqual((stage["range"], stage["remaining"], stage["decline"]), ({"min": 0, "max": top}, 7, True))
        args = (r["game"], r["revision"], "c1")
        for bad in ([top + 1], [-1], [True], ["1"], [], [0, 1], [1.0]):
            with self.subTest(bad=bad):
                self.assertEqual(p1.check(*args, bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        for count in (0, top):
            twin = L.ActionHost.from_state(state)
            s = twin.session(1)
            r = s.candidates()
            direct = A.submit(state, DrawMulliganCards(1, count), submitter=1)
            self.assertEqual(s.submit(r["game"], r["revision"], "c1", [count]).outcome, D.ACCEPTED)
            self.assertEqual(full_snap(twin.game.state), full_snap(direct.state))
            self.assertEqual(twin.game.state.players[1].mulligan_draws_remaining, 6)
        self.assertEqual(host.host_session().candidates()["empty_reason"], L.EMPTY_PLAYERS_TO_ACT)


class HostTest(unittest.TestCase):
    def janken_host(self):
        host, _ = L.ActionHost.start(*MULLIGAN_DECKS, 0)
        for _ in range(20):  # プレイヤーの準備（配置・補償）を U7 で終え、先攻を決める段階まで
            if host.game.state.phase is Phase.SETUP_FIRST_PLAYER:
                return host
            session = next(s for s in (host.session(0), host.session(1)) if s.candidates()["candidates"])
            r, _, ids = choose(session)
            self.assertEqual(session.submit(r["game"], r["revision"], "c1", ids).outcome, D.ACCEPTED)
        self.fail("先攻を決める段階に進まない")

    def test_janken_is_a_host_operation(self):
        host = self.janken_host()
        state = host.game.state
        for a in (0, 1):
            r = host.session(a).candidates()
            self.assertEqual((r["situation"], r["candidates"], r["empty_reason"]), (L.WAITING_FOR_HOST, [], L.EMPTY_HOST_OPERATION))
        hs = host.host_session()
        r, inputs = fetch(hs)
        self.assertEqual((r["actor"], r["candidates"][0]["kind"]), (L.HOST, L.KIND_REPORT_JANKEN))
        self.assertEqual((inputs["stages"][0]["range"], inputs["stages"][0]["meaning"]), ({"min": 0, "max": 1}, "player"))
        for bad in ([2], [-1], [True], ["0"], [], [0, 1]):
            with self.subTest(bad=bad):
                self.assertEqual(hs.check(r["game"], r["revision"], "c1", bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        for winner in (0, 1):
            twin = L.ActionHost.from_state(state)
            t = twin.host_session()
            rr = t.candidates()
            direct = A.submit(state, ReportJankenResult(winner))
            result = t.submit(rr["game"], rr["revision"], "c1", [winner])
            self.assertEqual((result.outcome, result.view), (D.ACCEPTED, direct.view_for(None)))
            self.assertEqual(full_snap(twin.game.state), full_snap(direct.state))
            self.assertEqual(twin.game.state.current_player, winner)

    def test_player_entry_cannot_become_host(self):
        host = self.janken_host()
        p0, hs = host.session(0), host.host_session()
        self.assertFalse(hasattr(p0, "host_session"))
        self.assertIsInstance(hs, L.HostSession)
        self.assertNotIsInstance(p0, L.HostSession)
        p0._actor = L.HOST  # 表示用の値を変えても、主体は窓口に固定（候補はプレイヤー 0 のまま）
        r = p0.candidates()
        self.assertEqual((r["actor"], r["candidates"]), (0, []))
        rh = hs.candidates()
        self.assertEqual(p0.submit(rh["game"], rh["revision"], "c1", [0]).refusal.code, L.CANDIDATES_WRONG_ACTOR)  # ホストの取っ手をプレイヤーは使えない
        self.assertEqual(hs.submit(r["game"], r["revision"], "c1", [0]).refusal.code, L.CANDIDATES_WRONG_ACTOR)  # プレイヤーの取っ手をホストは使えない
        with self.assertRaises(ValueError):
            host.session(L.HOST)

    def test_refusal_keeps_and_accept_invalidates_handles(self):
        host = self.janken_host()
        hs, p1 = host.host_session(), host.session(1)
        r1, rh = p1.candidates(), hs.candidates()
        self.assertEqual(hs.submit(rh["game"], rh["revision"], "c1", [5]).refusal.code, L.CANDIDATE_INPUT_INVALID)  # ホストの段の拒否
        self.assertNotEqual(p1.inputs(r1["game"], r1["revision"], "c9")["refusal"]["code"], L.CANDIDATES_STALE)  # プレイヤーの取っ手は失効しない
        self.assertEqual(hs.submit(rh["game"], rh["revision"], "c1", [1]).outcome, D.ACCEPTED)
        self.assertEqual(p1.inputs(r1["game"], r1["revision"], "c9")["refusal"]["code"], L.CANDIDATES_STALE)
        self.assertEqual(hs.inputs(rh["game"], rh["revision"], "c1")["refusal"]["code"], L.CANDIDATES_STALE)
        other = L.ActionHost.from_state(host.game.state)
        self.assertEqual(other.host_session().inputs(rh["game"], rh["revision"], "c1")["refusal"]["code"], L.CANDIDATES_WRONG_GAME)

    def test_internal_error_stops_the_host(self):
        host = self.janken_host()
        hs = host.host_session()
        r = hs.candidates()
        with mock.patch.object(A, "apply_command", side_effect=RuntimeError("テストの内部エラー")):
            result = hs.submit(r["game"], r["revision"], "c1", [0])
        self.assertEqual((result.outcome, result.view.status), (D.FAILED, D.UNAVAILABLE))
        for session in (hs, host.session(0)):
            with self.assertRaises(A.HostStoppedError):
                session.candidates()

    def test_queries_change_nothing(self):
        host = self.janken_host()
        before = snap(host.game.state)
        for _ in range(3):
            for session in (host.session(0), host.session(1), host.host_session()):
                r = session.candidates()
                session.inputs(r["game"], r["revision"], "c1")
                session.check(r["game"], r["revision"], "c1", [0])
                session.check(r["game"], r["revision"], "c1", [9])
        self.assertEqual(snap(host.game.state), before)


class SuddenDeathTest(unittest.TestCase):
    def sudden(self, seed=0, deck=None):
        state = H.build_test_state([{"active": SD.PIKA, "deck": deck or [SD.PIKA] + [H.FIRE] * 30, "prizes": 0},
                                    {"active": SD.PIKA, "deck": [SD.PIKA] + [H.FIRE] * 30, "prizes": 0}], current_player=0, seed=seed)
        return SD.constructed_sudden_death(SD.with_decklists(state))

    def test_start_is_a_host_operation_and_continues_to_setup(self):
        state = self.sudden()
        host = L.ActionHost.from_state(state)
        for a in (0, 1):
            r = host.session(a).candidates()
            self.assertEqual((r["situation"], r["empty_reason"]), (L.WAITING_FOR_HOST, L.EMPTY_HOST_OPERATION))  # 開始前は番の操作として扱わない
        hs = host.host_session()
        r, inputs = fetch(hs)
        cand = r["candidates"][0]
        self.assertEqual((cand["kind"], cand["processability"], inputs["stages"]), (L.KIND_START_SUDDEN_DEATH, L.MAY_STOP_LATER, []))
        self.assertEqual(hs.check(r["game"], r["revision"], "c1", [0])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        direct = A.submit(state, StartSuddenDeath())
        result = hs.submit(r["game"], r["revision"], "c1")
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(None)))
        self.assertEqual(full_snap(host.game.state), full_snap(direct.state))
        new = host.game.state
        self.assertEqual(new.segment_index, 1)
        if new.phase is Phase.SETUP_PLACEMENT:
            self.assertEqual(host.session(0).candidates()["candidates"][0]["kind"], L.KIND_PLACE_STARTING)

    def test_halted_extension_setup(self):
        for seed in range(200):
            for deck in ([SD.PIKA] + [H.FIRE] * 30, [SD.FOSSIL] * 4 + [SD.PIKA] + [H.FIRE] * 26):
                state = self.sudden(seed, deck)
                direct = A.submit(state, StartSuddenDeath())
                if direct.state is None or direct.state.phase is not Phase.HALTED:
                    continue
                host = L.ActionHost.from_state(state)
                hs = host.host_session()
                r = hs.candidates()
                result = hs.submit(r["game"], r["revision"], "c1")
                self.assertEqual((result.outcome, result.view), (D.ACCEPTED, direct.view_for(None)))
                self.assertEqual(result.view.status, D.HALTED)  # 延長戦の準備で止まった（既存の診断）
                for session in (hs, host.session(0)):
                    self.assertEqual(session.candidates()["situation"], L.HALTED)
                return
        self.fail("延長戦の準備で止まる盤面がない")


class TwinTest(unittest.TestCase):
    """山札の並びだけが違う双子（本人の手札・公開の情報は同じ）: 準備の候補・入力・入力の検査・不正な問い合わせの答えが同じ。"""

    def twin(self, state):
        other = state.clone()
        for p in other.players:
            p.deck = list(reversed(p.deck))
        for viewer in (0, 1, None):
            self.assertEqual(public_view(state, viewer), public_view(other, viewer))
        self.assertEqual(owned_card_ids(state, 0), owned_card_ids(other, 0))
        return other

    def responses(self, host):
        out = []
        for session in (host.session(0), host.session(1), host.host_session()):
            r = session.candidates()
            item = [without_handles(r)]
            for cand in ("c1", "c9"):
                item.append(session.inputs(r["game"], r["revision"], cand))
                item += [session.check(r["game"], r["revision"], cand, c) for c in ([], [0], [1], [2], ["o1"], ["o1", "o2"], ["o1", "o1"], "x")]
            out.append(item)
        return out

    def test_twins_in_placement_and_mulligan(self):
        host, _ = L.ActionHost.start(*MULLIGAN_DECKS, 0)
        a = host.game.state
        self.assertEqual(self.responses(L.ActionHost.from_state(a)), self.responses(L.ActionHost.from_state(self.twin(a))))
        m = MulliganTest("test_counts_and_who_draws").host().game.state
        self.assertEqual(self.responses(L.ActionHost.from_state(m)), self.responses(L.ActionHost.from_state(self.twin(m))))


class DocumentTest(unittest.TestCase):
    def test_document_records_the_scope(self):
        import pathlib

        text = (pathlib.Path(__file__).resolve().parent.parent / "docs" / "legal-actions-u7-2.md").read_text(encoding="utf-8")
        for phrase in ("ADOPT-U7-2", "host_session", "部分実装", "ReportJankenResult", "再監査"):
            self.assertTrue(phrase in text, phrase)


if __name__ == "__main__":
    unittest.main()
