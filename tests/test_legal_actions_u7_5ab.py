"""v0.167（U7-5a・U7-5b。docs/legal-actions-u7-5ab.md）: 場のポケモン 1 匹を指す操作（RemoveDisguise・DiscardFromPlay・RevealFaceDown）の候補・入力・検査・送信の回帰テスト。

確かめの種類を分ける:

- 構築盤面（既存の版のテストの盤面の作り。v0.47 のなにかの化石・ピッピ人形、v0.49 のタケシのキュウコンの「ばける」、v0.67 のマチスの秘策）: 候補・入力・処理可能性・
  情報境界（うらのカードの本当のカードだけを変えた双子）・取っ手・不正な入力・状態の不変
- 構築盤面からの合法な操作: U7 経由・client_api 経由・直接のコマンドの結果の一致、受理のあとの決定（バトル場に出す）・終局・処理のあとの停止（MH1）
- new_game からの合法な操作の列（3 つの規約集合。固定の seed）: 準備を U7 で終え、ピッピ人形を直接のコマンドで出し、U7 ですてる。同じコマンドを直接送った対戦と同じ状態

停止コードの文字列はテストの中に書かない（区分・ホストの段のコード・エンジンの例外の型で確かめる）。
"""

from __future__ import annotations

import json
import pathlib
import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.commands import (
    DiscardFromPlay,
    PlayTrainer,
    RemoveDisguise,
    RevealFaceDown,
)
from kyuura_engine.engine import (
    apply_command,
    check_discard_from_play,
    check_remove_disguise,
    check_reveal_face_down,
)
from kyuura_engine.errors import HiddenPropertyRead, IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.state import Phase
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_fossil_hidden_info_v0_47 as F
from tests import test_secret_plan_v0_67 as S
from tests import test_virtual_attacks_transformation_v0_49 as V
from tests.test_legal_actions_u7_1 import keys, snap, without_handles
from tests.test_legal_actions_u7_3 import (
    CONNECT_DECK,
    SETS,
    Recording,
    cand,
    host_of,
    inputs_of,
    setup_with_u7,
)
from tests.test_legal_actions_u7_4 import answer_with_u7

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
COMMANDS = {L.KIND_REMOVE_DISGUISE: RemoveDisguise, L.KIND_DISCARD_FROM_PLAY: DiscardFromPlay, L.KIND_REVEAL_FACE_DOWN: RevealFaceDown}


def disguised(**kw):
    """タケシのキュウコン（バトル場）に、手札のリザードを「ばける」でのせた盤面（プレイヤー 0 の番）。"""
    return V.shapeshift(V.ninetales_board(**kw), V.CHARMELEON)


def dolls():
    """バトル場になにかの化石、ベンチにコラッタと、水エネルギーのついたピッピ人形（プレイヤー 0 の番）。"""
    return F.board(F.FOSSIL, bench=[F.RATTATA, F.mon(F.CLEFAIRY_DOLL, (F.W,))])


def face_down(real):
    """マチスの秘策で ``real``（手札のカード）をうらにしてベンチに出した盤面（プレイヤー 0 の番）。"""
    return S.place(S.board(hand=(real,)), real)


def stage_of(state, kind, actor=0):
    _r, c, inputs = inputs_of(host_of(state).session(actor), kind)
    return c, (None if inputs is None else inputs["stages"][0])


def option_for(stage, pokemon_id):
    return next(o["id"] for o in stage["options"] if o["pokemon"] == pokemon_id)


def via_u7(state, kind, pokemon_id, *, actor=0):
    host = host_of(state.clone())
    session = host.session(actor)
    r, c, inputs = inputs_of(session, kind)
    return host, session.submit(r["game"], r["revision"], c["id"], [option_for(inputs["stages"][0], pokemon_id)])


def via_direct(state, command):
    game = A.HostedGame(state.clone())
    return game, game.submit(command, submitter=command.player)


class Same:
    def assert_same_as_direct(self, state, kind, pokemon_id):
        host, result = via_u7(state, kind, pokemon_id)
        game, direct = via_direct(state, COMMANDS[kind](0, pokemon_id))
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, game, result


class MappingTest(unittest.TestCase):
    """対応表（docs/legal-actions-u7-5ab.md 2 章）: 3 種類は既存の 3 つのコマンドだけ。ほかの入口は対応しない種類のまま（main は partial）。"""

    def test_kinds_and_coverage(self):
        r = host_of(disguised()).session(0).candidates()
        cov = r["coverage"]
        self.assertEqual(cov["completeness"], L.PARTIAL)
        self.assertEqual(cov["scope_kinds"], list(L.MAIN_KINDS))
        self.assertEqual(cov["not_covered_kinds"], ["use_power", "use_stadium", "check_face_up_deck"])  # v0.169（U7-5c）: play_trainer は対応した種類
        for kind in L.BOARD_KINDS:
            self.assertIn(kind, cov["implemented_kinds"])
        self.assertEqual(L.BOARD_KINDS, ("remove_disguise", "discard_from_play", "reveal_face_down"))
        kinds = [c["kind"] for c in r["candidates"]]
        self.assertEqual(kinds, sorted(kinds, key=L.MAIN_KINDS.index))  # 種類の並びは MAIN_KINDS の順

    def test_kinds_absent_when_impossible(self):
        r = host_of(F.board(F.mon(F.HITMONCHAN), bench=[F.RATTATA])).session(0).candidates()
        self.assertFalse(set(L.BOARD_KINDS) & {c["kind"] for c in r["candidates"]})  # ゲーム上できない種類は候補を作らない
        self.assertEqual(r["coverage"]["not_covered_kinds"], ["use_power", "use_stadium", "check_face_up_deck"])  # v0.169（U7-5c）: play_trainer は対応した種類

    def test_not_the_turn_player(self):
        for state in (disguised(), dolls(), face_down(S.DIGLETT)):
            r = host_of(state).session(1).candidates()
            self.assertEqual((r["situation"], r["candidates"]), (L.WAITING_FOR_PLAYER, []))


class RemoveDisguiseTest(Same, unittest.TestCase):
    def test_candidate_and_same_as_direct(self):
        state = disguised()
        c, stage = stage_of(state, L.KIND_REMOVE_DISGUISE)
        self.assertEqual((c["processability"], c["reasons"]), (L.MAY_STOP_LATER, [L.REASON_CONTINUATION]))
        self.assertEqual((stage["role"], stage["meaning"], stage["count"], stage["order"]), ("disguised", "pokemon", {"min": 1, "max": 1}, L.ORDER_NOT_APPLICABLE))
        ninetales = state.players[0].active
        self.assertEqual([(o["pokemon"], o["zone"], o["card_id"]) for o in stage["options"]], [(ninetales.pokemon_id, "active", V.BROCKS_NINETALES)])
        _host, game, result = self.assert_same_as_direct(state, L.KIND_REMOVE_DISGUISE, ninetales.pokemon_id)
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertIsNone(game.state.players[0].active.disguise)
        self.assertIn(ninetales.disguise, game.state.players[0].discard)

    def test_bench_and_only_disguised(self):
        bench = V.board(V.mon(V.RATTATA), bench=(V.mon(V.BROCKS_NINETALES),), hand=(V.CHARMELEON,))
        target = bench.players[0].bench[0]
        bench = V.shapeshift(bench, V.CHARMELEON, pokemon=target)
        _c, stage = stage_of(bench, L.KIND_REMOVE_DISGUISE)
        self.assertEqual([(o["pokemon"], o["zone"]) for o in stage["options"]], [(target.pokemon_id, "bench")])  # のせたカードのないポケモンは出さない
        self.assert_same_as_direct(bench, L.KIND_REMOVE_DISGUISE, target.pokemon_id)

    def test_max_hp_stop_after_acceptance_is_not_refused_before(self):
        """元の姿の HP がのっているダメージ以下（MH1）: 候補は may_stop_later（解除の結果を先読みしない）。送るとエンジンが処理のあとの確かめで拒否する（状態は変わらない）。"""
        state = disguised(opponent=V.mon(V.JIGGLYPUFF, (V.R,)))
        state.players[0].active.damage = 70  # 盤面を直接作る（v0.49 のテストと同じ）
        host = host_of(state.clone())
        session, other = host.session(0), host.session(1)
        theirs = other.candidates()
        r, c, inputs = inputs_of(session, L.KIND_REMOVE_DISGUISE)
        self.assertEqual(c["processability"], L.MAY_STOP_LATER)
        before = snap(host.game.state)
        result = session.submit(r["game"], r["revision"], c["id"], [inputs["stages"][0]["options"][0]["id"]])
        _game, direct = via_direct(state, RemoveDisguise(0, state.players[0].active.pokemon_id))
        self.assertEqual((result.outcome, direct.outcome), (D.REJECTED, D.REJECTED))
        self.assertEqual(result.view, direct.view_for(0))
        self.assertEqual(snap(host.game.state), before)
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o1"])["valid"])  # 拒否では取っ手を失効させない
        self.assertEqual(other.check(theirs["game"], theirs["revision"], "c1", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 相手の取っ手も失効しない


class DiscardFromPlayTest(Same, unittest.TestCase):
    def test_bench_doll_with_energy(self):
        state = dolls()
        c, stage = stage_of(state, L.KIND_DISCARD_FROM_PLAY)
        self.assertEqual((c["processability"], c["reasons"]), (L.SUPPORTED, []))  # 受理のあとの停止のもとが場にない（U7-3 と同じ条件）
        doll = state.players[0].bench[1]
        self.assertEqual([(o["zone"], o["card_id"]) for o in stage["options"]], [("active", F.MYSTERIOUS_FOSSIL), ("bench", F.CLEFAIRY_DOLL)])
        _host, game, result = self.assert_same_as_direct(state, L.KIND_DISCARD_FROM_PLAY, doll.pokemon_id)
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertEqual(sorted(game.state.cards[u].card_id for u in game.state.players[0].discard), sorted([F.CLEFAIRY_DOLL, F.W]))  # ついているカードもトラッシュ
        self.assertEqual((game.state.phase, game.state.decision), (Phase.MAIN, None))

    def test_active_fossil_then_promote_decision(self):
        state = F.board(F.FOSSIL, bench=[F.RATTATA])
        host, _game, result = self.assert_same_as_direct(state, L.KIND_DISCARD_FROM_PLAY, state.players[0].active.pokemon_id)
        self.assertEqual((result.outcome, host.game.state.decision.player), (D.ACCEPTED, 0))
        r = host.session(0).candidates()
        self.assertEqual([c["kind"] for c in r["candidates"]], [L.KIND_PROMOTE_ACTIVE])  # 受理のあとの決定は U7-1 の候補
        self.assertEqual(answer_with_u7(host).outcome, D.ACCEPTED)
        self.assertEqual((host.game.state.phase, host.game.state.current_player), (Phase.MAIN, 0))

    def test_lone_fossil_ends_the_game(self):
        state = F.board(F.FOSSIL, bench=[])
        host, _game, result = self.assert_same_as_direct(state, L.KIND_DISCARD_FROM_PLAY, state.players[0].active.pokemon_id)
        self.assertEqual((result.outcome, host.game.state.phase, host.game.state.result.winner), (D.ACCEPTED, Phase.GAME_OVER, 1))

    def test_evolved_fossil_and_ordinary_pokemon_are_not_offered(self):
        state = F.board(F.mon(F.OMANYTE), bench=[F.FOSSIL, F.RATTATA], opponent_bench=[F.DOLL])
        _c, stage = stage_of(state, L.KIND_DISCARD_FROM_PLAY)
        self.assertEqual([o["pokemon"] for o in stage["options"]], [state.players[0].bench[0].pokemon_id])  # 進化カードがのっている・相手の人形は出さない

    def test_retreat_candidate_with_active_fossil_does_not_break(self):
        """バトル場のなにかの化石（にげられるかが決まらない PF2）: 候補の取得は失敗せず、にげるは実行できない候補（選べるものなし）。すてる候補は出る。"""
        r = host_of(dolls()).session(0).candidates()
        retreat = cand(r, L.KIND_RETREAT)
        self.assertEqual((retreat["processability"], retreat["reasons"], retreat["input_stages"]), (L.RULING_UNRESOLVED, [L.REASON_STOPS], []))
        self.assertIsNotNone(cand(r, L.KIND_DISCARD_FROM_PLAY))

    def test_reactions_on_board_make_it_may_stop_later(self):
        state = S.place(S.board(hand=(S.DIGLETT,), bench=(F.DOLL,)), S.DIGLETT)  # うらのカードがある（受理のあとの停止のもとがありうる）
        _c, stage = stage_of(state, L.KIND_DISCARD_FROM_PLAY)
        doll = next(o for o in stage["options"] if o.get("card_id") == F.CLEFAIRY_DOLL)
        self.assertEqual((doll["processability"], doll["reasons"]), (L.MAY_STOP_LATER, [L.REASON_REACTIONS]))

    def test_own_face_down_card_is_fd1_shown_not_executable(self):
        """本人のうらのカード: エンジンの確かめは FD1（v0.67 からの挙動。本当のカードによらない）。U7 は選べるものとして示し、実行できない区分にする（送る前に断る）。"""
        state = face_down(S.DIGLETT)
        fd = S.face_down(state)[0]
        with self.assertRaises(HiddenPropertyRead):
            check_discard_from_play(state, DiscardFromPlay(0, fd.pokemon_id))
        _c, stage = stage_of(state, L.KIND_DISCARD_FROM_PLAY)
        option = stage["options"][0]
        self.assertEqual((option["pokemon"], option["face_down"], option["eligible"], option["processability"]), (fd.pokemon_id, True, False, L.RULING_UNRESOLVED))
        self.assertNotIn("card_id", option)
        host, result = via_u7(state, L.KIND_DISCARD_FROM_PLAY, fd.pokemon_id)
        self.assertEqual((result.outcome, result.refusal.code), (L.REFUSED, L.CANDIDATE_NOT_EXECUTABLE))
        _game, direct = via_direct(state, DiscardFromPlay(0, fd.pokemon_id))
        self.assertEqual(direct.outcome, D.REJECTED)  # 意図した差: 直接のコマンドはエンジンが拒否、U7 は送る前に断る（どちらも状態は変わらない）
        self.assertEqual(snap(host.game.state), snap(state))


class RevealFaceDownTest(Same, unittest.TestCase):
    def test_twins_have_the_same_responses_before_revealing(self):
        """うらのカードの本当のカード（たねポケモンのディグダ・たねでないユンゲラー）だけが違う双子: 実行前の候補・件数・並び・制約・理由・不正な入力への応答が同じ。"""
        responses = []
        for real in (S.DIGLETT, S.KADABRA):
            state = face_down(real)
            out = []
            for actor in (0, 1):
                session = host_of(state).session(actor)
                r = session.candidates()
                out.append(without_handles(r))
                for c in r["candidates"]:
                    out.append(session.inputs(r["game"], r["revision"], c["id"]))
                    for choices in ([], ["o1"], ["o2"], ["o1", "o1"], ["o9"], [1], "o1"):
                        out.append(session.check(r["game"], r["revision"], c["id"], choices))
            responses.append(out)
        self.assertEqual(responses[0], responses[1])
        text = json.dumps(responses[0], ensure_ascii=False)
        for secret in (S.DIGLETT, S.KADABRA, "ディグダ", "ユンゲラー"):
            self.assertNotIn(secret, text)  # うらのカードのカード id・名前を返さない

    def test_candidate_shape(self):
        state = face_down(S.DIGLETT)
        fd = S.face_down(state)[0]
        c, stage = stage_of(state, L.KIND_REVEAL_FACE_DOWN)
        self.assertEqual((c["processability"], c["reasons"]), (L.MAY_STOP_LATER, [L.REASON_FACE_DOWN]))
        self.assertEqual(stage["options"], [{"id": "o1", "pokemon": fd.pokemon_id, "card": fd.card, "zone": "bench", "bench_index": 0, "face_down": True,
                                             "eligible": True, "processability": L.MAY_STOP_LATER, "reasons": [L.REASON_FACE_DOWN]}])

    def test_results_differ_only_after_revealing(self):
        stays = face_down(S.DIGLETT)
        _host, game, result = self.assert_same_as_direct(stays, L.KIND_REVEAL_FACE_DOWN, S.face_down(stays)[0].pokemon_id)
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertFalse(game.state.face_down_cards)
        self.assertEqual(len(game.state.players[0].bench), 1)
        trashed = face_down(S.KADABRA)
        _host, game, result = self.assert_same_as_direct(trashed, L.KIND_REVEAL_FACE_DOWN, S.face_down(trashed)[0].pokemon_id)
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertEqual(len(game.state.players[0].bench), 0)
        kinds = [e["kind"] for e in game.state.log[len(trashed.log):]]
        self.assertEqual(kinds[:2], ["secret_plan_revealed", "secret_plan_discarded"])  # 公開は実行のあと（既存のログ・観測）

    def test_face_down_active_trashed_then_promote(self):
        state = face_down(S.KADABRA)
        state = S.to_active(state, S.face_down(state)[0])
        active = state.players[0].active
        self.assertTrue(state.is_face_down(active))
        host, _game, result = self.assert_same_as_direct(state, L.KIND_REVEAL_FACE_DOWN, active.pokemon_id)
        self.assertEqual((result.outcome, host.game.state.decision.player), (D.ACCEPTED, 0))
        self.assertEqual([c["kind"] for c in host.session(0).candidates()["candidates"]], [L.KIND_PROMOTE_ACTIVE])
        self.assertEqual(answer_with_u7(host).outcome, D.ACCEPTED)

    def test_face_down_active_retreat_withholds_inputs(self):
        """自分のうらのバトル場のポケモン: にげるエネルギーが決まらない（FD1）。v0.166 までは候補の取得が失敗していた。にげるは unverified で、入力を返さない（双子で同じ）。"""
        seen = []
        for real in (S.DIGLETT, S.KADABRA):
            state = face_down(real)
            state = S.to_active(state, S.face_down(state)[0])
            session = host_of(state).session(0)
            r = session.candidates()
            retreat = cand(r, L.KIND_RETREAT)
            self.assertEqual((retreat["processability"], retreat["input_disclosure"]), (L.UNVERIFIED, L.DISCLOSURE_UNCONFIRMED))
            inputs = session.inputs(r["game"], r["revision"], retreat["id"])
            self.assertEqual((inputs["stages"], inputs["withheld"]["code"]), ([], L.INPUT_BOUNDARY_UNCONFIRMED))
            seen.append((without_handles(r), inputs["stages"]))
        self.assertEqual(seen[0], seen[1])

    def test_check_reads_no_hidden_property(self):
        """確かめはうらのカードの決まらない項目を読まない（読めば HiddenPropertyRead）。ふつうのカード・相手のポケモンはゲーム上できない。"""
        state = face_down(S.KADABRA)
        fd = S.face_down(state)[0]
        self.assertIs(check_reveal_face_down(state, RevealFaceDown(0, fd.pokemon_id)), fd)
        for pid, code in ((state.players[0].active.pokemon_id, "NOT_FACE_DOWN"), (state.players[1].active.pokemon_id, "POKEMON_NOT_YOURS")):
            with self.assertRaises(IllegalActionError) as caught:
                check_reveal_face_down(state, RevealFaceDown(0, pid))
            self.assertEqual(caught.exception.code, code)


class CheckFunctionTest(unittest.TestCase):
    """関数にした確かめが、コマンドの処理と同じ拒否（コード）になる（補助関数の確かめ）。"""

    def test_same_codes_as_commands(self):
        cases = [(disguised(), check_remove_disguise, RemoveDisguise), (dolls(), check_discard_from_play, DiscardFromPlay),
                 (face_down(S.DIGLETT), check_reveal_face_down, RevealFaceDown)]
        for state, check, command in cases:
            for actor in (0, 1):
                for pid in [q.pokemon_id for side in state.players for q in side.in_play()] + [999]:
                    cmd = command(actor, pid)
                    try:
                        check(state, cmd)
                        expected = None
                    except IllegalActionError as error:
                        expected = error.code
                    try:
                        apply_command(state, cmd)
                        found = None
                    except IllegalActionError as error:
                        found = error.code
                    self.assertEqual(found, expected, cmd)


class SessionContractTest(unittest.TestCase):
    STATES = (disguised, dolls, lambda: face_down(S.KADABRA))

    def test_queries_change_nothing(self):
        for make in self.STATES:
            host = host_of(make())
            before = snap(host.game.state)
            session = host.session(0)
            for _ in range(2):
                r = session.candidates()
                for c in r["candidates"]:
                    session.inputs(r["game"], r["revision"], c["id"])
                    for choices in ([], ["o1"], ["o2"], ["o1", "o2"], ["o1", "o1"], ["o9"], [1]):
                        session.check(r["game"], r["revision"], c["id"], choices)
            self.assertEqual(snap(host.game.state), before)

    def test_invalid_inputs_and_handles(self):
        for make, kind in ((disguised, L.KIND_REMOVE_DISGUISE), (dolls, L.KIND_DISCARD_FROM_PLAY), (lambda: face_down(S.DIGLETT), L.KIND_REVEAL_FACE_DOWN)):
            with self.subTest(kind=kind):
                host = host_of(make())
                session, other = host.session(0), host.session(1)
                r, c, _ = inputs_of(session, kind)
                for choices in ([], ["o9"], ["o1", "o1"], ["o1", "o2"], [0], "o1", None):
                    self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)
                self.assertEqual(other.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
                self.assertEqual(session.check("other", r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o9"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
                self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o1"])["valid"])  # 拒否では失効しない
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).outcome, D.ACCEPTED)
                self.assertEqual(session.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効

    def test_no_verifier_values(self):
        for make in self.STATES:
            session = host_of(make()).session(0)
            r = session.candidates()
            payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
            self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
            self.assertNotIn("seed", json.dumps(payload))


class ClientApiTest(unittest.TestCase):
    def test_three_kinds_through_client_api(self):
        for make, kind, pick in ((disguised, L.KIND_REMOVE_DISGUISE, lambda s: s.players[0].active.pokemon_id),
                                 (dolls, L.KIND_DISCARD_FROM_PLAY, lambda s: s.players[0].bench[1].pokemon_id),
                                 (lambda: face_down(S.KADABRA), L.KIND_REVEAL_FACE_DOWN, lambda s: S.face_down(s)[0].pokemon_id)):
            with self.subTest(kind=kind):
                state = make()
                pid = pick(state)
                hub = ClientHub.from_state(state.clone())
                me = hub.player(0)
                r = me.handle({**CONTRACT, "type": "candidates"})["response"]
                c = cand(r, kind)
                fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
                stage = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"][0]
                choices = [option_for(stage, pid)]
                self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
                bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": ["o9"]})
                self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
                self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 断りは相手・観戦者へ知らせない
                sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
                self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
                game, _ = via_direct(state, COMMANDS[kind](0, pid))
                updates = {a: hub.take_updates(a) for a in (1, "spectator")}
                self.assertEqual(updates["spectator"][-1]["observation"], observe(game.state, None))
                self.assertEqual(updates[1][-1]["observation"], observe(game.state, 1))

    def test_engine_rejection_is_private(self):
        state = disguised(opponent=V.mon(V.JIGGLYPUFF, (V.R,)))
        state.players[0].active.damage = 70
        hub = ClientHub.from_state(state)
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_REMOVE_DISGUISE)
        sent = me.handle({**CONTRACT, "type": "submit", "game": r["game"], "revision": r["revision"], "candidate": c["id"], "choices": ["o1"]})
        self.assertEqual(sent["outcome"], D.REJECTED)
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 拒否の存在を相手・観戦者へ知らせない


def _doll_deck():
    deck = list(CONNECT_DECK)
    for _ in range(4):
        deck.remove(H.FIRE)
    return deck + [H.CLEFAIRY_DOLL] * 4


DOLL_DECK = _doll_deck()  # U7-3 の接続のデッキの炎エネルギー 4 枚をピッピ人形にした（60 枚。並びは切る前のデッキの並び）
DOLL_SEED = 1  # 先攻（プレイヤー 0）の最初の番の手札にピッピ人形がある seed（3 つの規約集合で同じ）


class ConnectionTest(unittest.TestCase):
    """new_game からの合法な操作の列（固定の seed）: 準備を U7 で終え、ピッピ人形を直接のコマンドで出し（トレーナーは U7-5c）、U7 ですてて番を終える。直接の列と同じ状態。"""

    def test_from_new_game_with_three_sets(self):
        self.assertEqual(len(DOLL_DECK), 60)
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(DOLL_DECK, DOLL_DECK, DOLL_SEED, **options)
                self.assertEqual(start.outcome, D.ACCEPTED)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                state = host.game.state
                self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 0))
                doll = next(u for u in state.players[0].hand if state.cards[u].card_id == H.CLEFAIRY_DOLL)
                self.assertEqual(recording.submit(PlayTrainer(0, doll), submitter=0).outcome, D.ACCEPTED)
                host.invalidate()  # ホストの外で状態が変わった（直接のコマンド）ので、取っ手を取り直す
                pid = next(q.pokemon_id for q in host.game.state.players[0].in_play() if q.card == doll)
                session = host.session(0)
                r, c, inputs = inputs_of(session, L.KIND_DISCARD_FROM_PLAY)
                self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [option_for(inputs["stages"][0], pid)]).outcome, D.ACCEPTED)
                r = session.candidates()
                self.assertEqual(session.submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"], []).outcome, D.ACCEPTED)
                direct = A.HostedGame(start.state.clone())
                for command, submitter in recording.sent:
                    self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                self.assertEqual(snap(direct.state), snap(host.game.state))
                self.assertTrue(any(isinstance(command, DiscardFromPlay) for command, _ in recording.sent))


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-5ab.md").read_text(encoding="utf-8")
        for phrase in ("RemoveDisguise", "DiscardFromPlay", "RevealFaceDown", "check_remove_disguise", "check_discard_from_play", "check_reveal_face_down",
                       "may_stop_later", "supported", "partial", "kyuura-client-api", "FD1", "MH1", "F-1", "3649946", "R-1", "R-2"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
