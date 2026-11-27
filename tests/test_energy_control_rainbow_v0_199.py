"""v0.199: ミュウツー（PR1-022）の［エナジーコントロール］で、相手の場についているレインボーエネルギーを特殊エネルギーカードとして選べるものから外す
（docs/energy-control-rainbow-v0.199.md）。

ワザの文面「相手の場のエネルギーカード(特殊エネルギー以外)を1枚選んではがす」と、レインボーエネルギーが特殊エネルギーのカードであることに基づく実装解釈（当時の直接裁定は
未確認）。v0.198 までは、選べるカードがレインボーエネルギーだけなら宣言の前の先読みで RB3（``UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD``）の拒否、ほかの基本エネルギー
カードがあれば選べるが選ぶと止める選択だった。

- 旧 seed 9083 相当（相手の場はレインボーエネルギーと無色2個エネルギーだけ）: 宣言が受理され、「おもて」でも決定を出さずにワザを終える（付け替えなし）。「うら」は失敗
- 基本エネルギーとレインボーエネルギーの共存: 基本エネルギーカードだけが選べるものに出て、選んだ相手のポケモンへ実際に付け替えられる
- 対照: 対象 0 枚（エネルギーなし）・基本エネルギーだけ
- 直接のコマンドと候補 API（candidates → inputs → check → submit）、コインと公開のログ、決定と番の進行
- 同じ停止コードを使うほかの処理（ミュウのレインボーウェーブ・わるいレアコイルのじりょくせん）は今までどおり RB3 で止まる
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import ResolveDecision, UseAttack
from kyuura_engine import effects as E
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import MOVE_OPPONENT_ENERGY, SELECT_POKEMON
from kyuura_engine.engine import check_invariants
from kyuura_engine.observation import visible_log
from kyuura_engine.replay_record import checks
from tests import helpers as H
from tests.helpers import apply_kernel, build_test_state, with_coin_results
from tests.test_neo_trainer_components_v0_80 import rejects
from tools.verification_ai.fixtures_observe import FixtureGame

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "energy-control-rainbow-v0.199.md"
MEWTWO, BUL, P, G, L, DCE, RAINBOW = "PR1-022", "PMCG1-001", "PMCG1-101", "PMCG1-097", "PMCG1-100", "PMCG1-096", H.RAINBOW_ENERGY
MEW_SI, DARK_MAGNETON = "SI-004", "PMCG4-030"  # ミュウ（レインボーウェーブ）・わるいレアコイル（ソニックブーム・じりょくせん。コイルから進化）
RB3 = E.RAINBOW_BASIC_CODE
HD, TL = CoinSide.HEADS, CoinSide.TAILS
CONTRACT = {"contract": "kyuura-client-api", "format": 1}


def board(opp_active_energy=(), opp_bench_energy=(), *, active=None, opponent=None):
    me = {"active": active or {"card": MEWTWO, "energy": [P, G]}, "bench": [H.RATTATA], "hand": [], "deck": [G] * 10, "discard": [], "prizes": 6}
    them = {"active": opponent or {"card": BUL, "energy": list(opp_active_energy)}, "bench": [{"card": BUL, "energy": list(opp_bench_energy)}], "hand": [],
            "deck": [G] * 10, "discard": [], "prizes": 6}
    return build_test_state([me, them], turn_number=7, current_player=0)


OLD_9083 = ((), (DCE, RAINBOW))
MIXED = ((G,), (DCE, RAINBOW))
NONE = ((), ())
BASIC_ONLY = ((G,), (G,))


def attack(state, *coins):
    return apply_kernel(with_coin_results(state, *coins), UseAttack(0, 0))


def answer(state, choice):
    return apply_kernel(state, ResolveDecision(0, state.decision.id, (choice,)))


def kinds(before, after):
    return [e["kind"] for e in after.log[len(before.log):]]


def public(before, after):
    return [e["kind"] for e in visible_log(after, None)[len(visible_log(before, None)):]]


class DirectCommandTest(unittest.TestCase):
    def test_old_9083_board_is_accepted_and_heads_moves_nothing(self):
        state = board(*OLD_9083)
        rainbow = state.players[1].bench[0].energy[1]
        self.assertEqual(E.opponent_field_energy_options(state, 0), ())
        used = attack(state, HD)
        self.assertIsNone(used.decision)  # 対象 0 枚: 付け替えの決定を出さない
        self.assertEqual([e["result"] for e in used.log[len(state.log):] if e["kind"] == "coin_flip"], ["heads"])
        self.assertNotIn("move_opponent_energy", kinds(state, used))
        self.assertEqual([p.energy for p in used.players[1].in_play()], [p.energy for p in state.players[1].in_play()])
        self.assertIn(rainbow, used.players[1].bench[0].energy)
        self.assertEqual(public(state, used)[:2], ["attack", "coin_flip"])
        self.assertEqual((used.current_player, used.turn_number), (1, 8))  # ワザで番が終わる
        check_invariants(used)

    def test_tails_fails_on_every_board(self):
        for spec in (OLD_9083, MIXED, NONE, BASIC_ONLY):
            with self.subTest(spec=spec):
                state = board(*spec)
                used = attack(state, TL)
                self.assertEqual([e["reason"] for e in used.log[len(state.log):] if e["kind"] == "attack_failed"], ["coin"])
                self.assertIsNone(used.decision)
                self.assertEqual([p.energy for p in used.players[1].in_play()], [p.energy for p in state.players[1].in_play()])
                self.assertEqual(used.current_player, 1)

    def test_mixed_board_offers_only_the_basic_card_and_moves_it(self):
        state = board(*MIXED)
        grass = state.players[1].active.energy[0]
        bench = state.players[1].bench[0]
        used = attack(state, HD)
        self.assertEqual((used.decision.kind, used.decision.options, used.decision.context_value("unresolved_choices", ())), (MOVE_OPPONENT_ENERGY, (grass,), ()))
        chosen = answer(used, grass)
        self.assertEqual((chosen.decision.kind, chosen.decision.options), (SELECT_POKEMON, tuple(p.pokemon_id for p in state.players[1].in_play())))
        moved = answer(chosen, bench.pokemon_id)
        self.assertEqual(moved.players[1].active.energy, [])
        self.assertEqual(moved.players[1].bench[0].energy, [*bench.energy, grass])  # 無色2個・レインボーはそのまま、草が加わる
        ev = [e for e in moved.log[len(chosen.log):] if e["kind"] == "move_opponent_energy"]
        self.assertEqual([(e["energy"], e["to_pokemon_id"]) for e in ev], [(grass, bench.pokemon_id)])
        self.assertIn("move_opponent_energy", public(chosen, moved))
        self.assertIsNone(moved.decision)
        self.assertEqual(moved.current_player, 1)
        check_invariants(moved)

    def test_controls_no_energy_and_basic_only(self):
        none = board(*NONE)
        used = attack(none, HD)
        self.assertIsNone(used.decision)
        self.assertNotIn("move_opponent_energy", kinds(none, used))
        basic = board(*BASIC_ONLY)
        used = attack(basic, HD)
        self.assertEqual(used.decision.options, (basic.players[1].active.energy[0], basic.players[1].bench[0].energy[0]))
        self.assertEqual(used.decision.context_value("unresolved_choices", ()), ())


def req(endpoint, kind, **fields):
    return json.loads(json.dumps(endpoint.handle(json.loads(json.dumps({**CONTRACT, "type": kind, **fields}, ensure_ascii=False))), ensure_ascii=False))


class CandidateApiTest(unittest.TestCase):
    def _send(self, ep, kind, pick):
        cands = req(ep, "candidates")["response"]
        c = next(x for x in cands["candidates"] if x["kind"] == kind)
        handle = {"game": cands["game"], "revision": cands["revision"], "candidate": c["id"]}
        stage = req(ep, "inputs", **handle)["response"]["stages"][0]
        opt = next(o for o in stage["options"] if pick(o))
        chk = req(ep, "check", **handle, choices=[opt["id"]])
        self.assertTrue(chk["response"]["valid"])
        return stage, req(ep, "submit", **handle, choices=[opt["id"]], operation_id=f"t199-{kind}-{opt['id']}")

    def test_old_9083_board_check_and_submit_accept(self):
        game = FixtureGame(with_coin_results(board(*OLD_9083), HD))
        hub = ClientHub(game, verifier=lambda *a, **k: None)
        before = checks(game.state)
        _stage, sub = self._send(hub.player(0), "use_attack", lambda o: o.get("name_ja") == "エナジーコントロール")
        self.assertEqual(sub["outcome"], "accepted")
        self.assertNotEqual(checks(game.state), before)
        self.assertIsNone(game.state.decision)
        self.assertEqual(game.state.current_player, 1)
        self.assertGreater(len(hub.take_updates(1)), 0)

    def test_mixed_board_answers_through_the_api(self):
        state = board(*MIXED)
        grass, target = state.players[1].active.energy[0], state.players[1].bench[0].pokemon_id
        game = FixtureGame(with_coin_results(state, HD))
        ep = ClientHub(game, verifier=lambda *a, **k: None).player(0)
        _s, sub = self._send(ep, "use_attack", lambda o: o.get("name_ja") == "エナジーコントロール")
        self.assertEqual(sub["outcome"], "accepted")
        stage, sub = self._send(ep, "answer_decision", lambda o: o.get("card") == grass)
        self.assertEqual([o.get("card") for o in stage["options"]], [grass])  # レインボーエネルギーは選べるものに出ない
        self.assertEqual(sub["outcome"], "accepted")
        _s, sub = self._send(ep, "answer_decision", lambda o: o.get("value") == target)
        self.assertEqual(sub["outcome"], "accepted")
        self.assertIn(grass, game.state.players[1].bench[0].energy)
        self.assertEqual(game.state.current_player, 1)


class OtherRb3PathsTest(unittest.TestCase):
    """同じ停止コードを使うほかの処理には当てはめない（今までどおり RB3 で止まる）。"""

    def test_rainbow_wave_still_stops(self):
        state = board(active={"card": MEW_SI, "energy": [RAINBOW]})
        rejects(self, state, UseAttack(0, 0), RB3)

    def test_magnetic_lines_still_stops(self):
        state = board(active={"card": DARK_MAGNETON, "energy": [L, L], "evolved_from": H.MAGNEMITE}, opponent={"card": BUL, "energy": [RAINBOW]})
        rejects(self, state, UseAttack(0, 1), RB3)  # 相手の対戦ポケモンのレインボーエネルギー（控えあり）
        self.assertIsNotNone(apply_kernel(state, UseAttack(0, 0)))  # ソニックブームは受理


class DocumentTest(unittest.TestCase):
    def test_record_of_the_interpretation(self):
        text = DOC.read_text(encoding="utf-8")
        for needed in ("カード文面とカード分類に基づく実装解釈。当時の直接裁定は未確認", "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD", "PR1-022", "0.199.0"):
            self.assertIn(needed, text)


if __name__ == "__main__":
    unittest.main()
