"""v0.160（U7-1。docs/legal-actions-u7-1.md）: 合法手 API の最小の実装（決定への回答・番を終える）の回帰テスト。

確かめの種類を分ける:

- 構築盤面（``build_test_state``）: パソコン通信・エネルギー回収の決定（複数の選択・枚数・任意の辞退・始まった検索）、ポケモンチェックのきぜつ、双子の盤面
- 補助の作り（状態の写しの決定を差し替える）: 選ぶと止める選択・続けられない決定・見えないカードの選べるもの（実行時の確かめ）
- new_game からの合法な操作の列（方策の操作をホストが送り、決定と番を終える操作だけ U7 を通す）: 準備・終局・延長戦の開始待ち・停止・3 つの規約集合・直接の送信と同じ結果

停止コードの文字列はテストの中に書かない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import apply_command
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine import snapshot as SN
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import (
    EndTurn,
    PlayTrainer,
    PromoteActive,
    ResolveDecision,
    StartSuddenDeath,
    TakePrize,
    UseAttack,
)
from kyuura_engine.observation import OPTION_MEANINGS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.state import Phase
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
from tests import test_final_pmcg_cards_v0_68 as T68
from tests import test_movement_damage_reactions_v0_87 as T87
from tests import test_pokemon_tools_stadiums_v0_81 as T81
from tests.log_audit import owned_card_ids, public_view
from tests.test_replay_record_v0_153 import DECKS, HALT_DECK
from tests.test_replay_run_v0_154 import DRY_DECKS, dry_command

SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")


def snap(state):
    """状態・乱数・ログ・決定の通し番号（候補の取得で変わらないことを確かめる値）。"""
    return state_to_dict(state, format_version=35), rng_fingerprint(state.rng), len(state.log), state.next_decision_id


def keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys(v)


def without_handles(response):
    data = copy.deepcopy(response)
    for key in ("game", "revision"):
        data.pop(key, None)
    return data


def search_board(hand=(H.FIRE, H.PONYTA), deck=(H.WATER, H.SEEL, H.BILL, H.FIRE), prizes=(H.POTION, H.WATER), trainer=H.COMPUTER_SEARCH):
    """自分（プレイヤー 0）の番の MAIN。手札の先頭がトレーナー。"""
    return H.build_test_state([
        {"active": H.GROWLITHE, "hand": [trainer, *hand], "deck": list(deck), "prizes": list(prizes)},
        {"active": H.STARYU, "bench": [H.SEEL], "hand": [H.WATER], "deck": [H.WATER, H.WATER], "prizes": [H.WATER, H.WATER]},
    ], turn_number=3)


def host_after_trainer(state):
    host = L.ActionHost(A.HostedGame(state))
    assert host.game.submit(PlayTrainer(0, state.players[0].hand[0]), submitter=0).outcome == D.ACCEPTED
    return host


def fetch(session):
    r = session.candidates()
    return r, (session.inputs(r["game"], r["revision"], r["candidates"][0]["id"]) if r["candidates"] else None)


def with_decision(state, **changes):
    new = state.clone()
    new.decision = dataclasses.replace(state.decision, **changes)
    return new


# ---------------------------------------------------------------- new_game からの合法な操作の列


def submitter(command):
    player = getattr(command, "player", None)
    return player if player in (0, 1) else None


def u7_send(host, command):
    """方策のコマンドが決定への回答か番を終える操作なら、U7 の候補と入力で送る（そうでなければ None）。"""
    state = host.game.state
    if isinstance(command, EndTurn):
        session = host.session(command.player)
        r = session.candidates()
        (cand,) = [c for c in r["candidates"] if c["kind"] == L.KIND_END_TURN]
        return session.submit(r["game"], r["revision"], cand["id"])
    if not isinstance(command, (ResolveDecision, TakePrize, PromoteActive)):
        return None
    d = state.decision
    if isinstance(command, ResolveDecision):
        values = command.choices
    elif isinstance(command, TakePrize):
        values = (command.index,)
    else:
        values = tuple(p.pokemon_id for p in state.players[command.player].bench if p.card == command.pokemon)
    session = host.session(d.player)
    r, inputs = fetch(session)
    if "withheld" in inputs:  # 情報境界を確かめていない決定: U7 は入力を返さない。ホストが直接送る（U7 の外）
        WITHHELD.add(d.kind)
        return None
    stage = inputs["stages"][0]
    choices = list(values) if stage["input"] == L.INPUT_CHOOSE_VALUE else [f"o{d.options.index(v) + 1}" for v in values]
    return session.submit(r["game"], r["revision"], r["candidates"][0]["id"], choices)


WITHHELD: set[str] = set()


def drive(seed, *, use_u7, conventions=None, deck=None, max_steps=4000, until=None):
    options = {} if conventions is None else {"conventions": conventions}
    decks = (deck, deck) if deck is not None else DECKS
    host, start = L.ActionHost.start(*decks, seed, **options)
    assert start.outcome == D.ACCEPTED
    for _ in range(max_steps):
        state = host.game.state
        if state.phase in (Phase.GAME_OVER, Phase.HALTED, Phase.SUDDEN_DEATH) or (until is not None and until(state)):
            break
        command = H.trainer_policy_command(state, janken_winner=seed % 2)
        result = u7_send(host, command) if use_u7 else None
        if result is None:
            result = host.game.submit(command, submitter=submitter(command))
        assert result.outcome == D.ACCEPTED, (command, result)
    return host


def setUpModule():
    global OVER, SUDDEN
    OVER = drive(0, use_u7=True)
    SUDDEN = drive(9, use_u7=True)


class DecisionKindsTest(unittest.TestCase):
    def test_every_option_meaning_is_handled(self):
        handled = {"card", "pokemon", "position", "number", "color", "name", "janken", "peek_target", "value"}
        self.assertLessEqual(set(OPTION_MEANINGS.values()), handled)

    def test_unknown_or_unsupported_decision_is_shown_not_removed(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        broken = with_decision(host.game.state, kind="future_kind_for_test")
        host.replace_game(A.HostedGame(broken))
        session = host.session(0)
        r, inputs = fetch(session)
        (cand,) = r["candidates"]
        self.assertEqual((cand["kind"], cand["processability"]), (L.KIND_ANSWER_DECISION, L.NOT_IMPLEMENTED))
        self.assertEqual(inputs["stages"], [])
        before = snap(host.game.state)
        result = session.submit(r["game"], r["revision"], cand["id"], ["o1"])
        self.assertEqual((result.outcome, result.refusal.code), (L.REFUSED, L.CANDIDATE_NOT_EXECUTABLE))
        self.assertEqual(snap(host.game.state), before)


class AnswerTest(unittest.TestCase):
    def setUp(self):
        self.host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA, H.POTION)))
        self.p0, self.p1 = self.host.session(0), self.host.session(1)

    def test_multiple_choice_count_and_distinct(self):
        r, inputs = fetch(self.p0)
        self.assertEqual((r["situation"], r["coverage"]["completeness"]), (L.ACTOR_TO_ACT, L.COMPLETE))
        stage = inputs["stages"][0]
        self.assertEqual((stage["input"], stage["count"], stage["decline"], stage["distinct"]), (L.INPUT_CHOOSE_OPTION, {"min": 2, "max": 2}, False, True))
        hand = self.host.game.state.players[0].hand
        self.assertEqual([o["card"] for o in stage["options"]], list(hand))  # 自分の手札（見えるカード）は uid と card_id
        args = (r["game"], r["revision"], "c1")
        for bad in (["o1"], ["o1", "o1"], ["o1", "o9"], ["o0", "o1"], ["1", "2"], "o1o2", [1, 2], ["o1", "o2", "o3"]):
            with self.subTest(bad=bad):
                self.assertEqual(self.p0.check(*args, bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertTrue(self.p0.check(*args, ["o1", "o2"])["valid"])

    def test_order_is_preserved_and_same_as_direct_submission(self):
        state = self.host.game.state
        r, _ = fetch(self.p0)
        direct = A.submit(state, ResolveDecision(0, state.decision.id, (state.decision.options[1], state.decision.options[0])), submitter=0)
        result = self.p0.submit(r["game"], r["revision"], "c1", ["o2", "o1"])
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertEqual(snap(self.host.game.state), snap(direct.state))
        self.assertEqual(result.view, direct.view_for(0))

    def test_search_started_shows_actual_deck_cards(self):
        r, _ = fetch(self.p0)
        self.p0.submit(r["game"], r["revision"], "c1", ["o1", "o2"])
        state = self.host.game.state
        _, inputs = fetch(self.p0)
        stage = inputs["stages"][0]
        self.assertEqual(stage["decision_kind"], "search_deck")
        self.assertEqual([o["card"] for o in stage["options"]], list(state.decision.options))
        self.assertEqual({o["card_id"] for o in stage["options"]}, {state.cards[u].card_id for u in state.players[0].deck})

    def test_other_player_gets_no_candidates_or_identifiers(self):
        r1 = self.p1.candidates()
        self.assertEqual((r1["situation"], r1["candidates"], r1["coverage"]["completeness"]), (L.WAITING_FOR_PLAYER, [], L.COMPLETE))
        state = self.host.game.state
        text = json.dumps(r1)
        for key in ("options", "card", "card_id", "decision_kind"):
            self.assertNotIn(f'"{key}"', text)
        r0 = self.p0.candidates()
        for call in (lambda: self.p1.inputs(r0["game"], r0["revision"], "c1"), lambda: self.p1.check(r0["game"], r0["revision"], "c1", ["o1", "o2"])):
            self.assertEqual(call()["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        result = self.p1.submit(r0["game"], r0["revision"], "c1", ["o1", "o2"])
        self.assertEqual((result.refusal.code, result.view), (L.CANDIDATES_WRONG_ACTOR, None))
        self.assertIs(self.host.game.state, state)
        for actor in (None, 2, True, "0"):
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                self.host.session(actor)

    def test_responses_have_no_verifier_values(self):
        r, inputs = fetch(self.p0)
        for data in (r, inputs, self.p1.candidates()):
            json.dumps(data)
            self.assertFalse(set(keys(data)) & FORBIDDEN_KEYS, data)
            self.assertNotIn("command", set(keys(data)))

    def test_queries_change_nothing_and_do_not_use_the_engine_rng(self):
        state = self.host.game.state
        before = snap(state)
        for _ in range(5):
            r, _ = fetch(self.p0)
            self.p0.check(r["game"], r["revision"], "c1", ["o1"])
            self.p0.check(r["game"], r["revision"], "c1", ["o1", "o2"])
            self.p1.candidates()
            self.p0.submit(r["game"], r["revision"], "c1", ["o1", "o1"])  # ホストの段で拒否
        self.assertIs(self.host.game.state, state)
        self.assertEqual(snap(state), before)

    def test_invalid_queries_get_fixed_answers(self):
        r, _ = fetch(self.p0)
        cases = [(("other", r["revision"], "c1"), L.CANDIDATES_WRONG_GAME), ((r["game"], "0" * 32, "c1"), L.CANDIDATES_STALE),
                 ((r["game"], None, "c1"), L.CANDIDATES_STALE), ((r["game"], r["revision"], "c9"), L.CANDIDATE_UNKNOWN), ((7, r["revision"], "c1"), L.CANDIDATES_WRONG_GAME)]
        for args, code in cases:
            with self.subTest(args=args):
                answer = self.p0.inputs(*args)
                self.assertEqual(answer["refusal"]["code"], code)
                self.assertEqual(answer["refusal"]["message"], L.REFUSAL_MESSAGES[code])
                self.assertEqual(self.p0.submit(*args, ["o1", "o2"]).refusal.code, code)


class OptionalAndStopTest(unittest.TestCase):
    def test_optional_decline(self):
        """手札を好きなだけトラッシュする「のぞむなら」のトレーナー（PMCG5-088）: 0 枚を選ぶ（辞退）が受理される。数の選択（PMCG5-083）の値も同じ入口。"""
        host = host_after_trainer(search_board((H.FIRE, H.WATER), trainer="PMCG5-088"))
        p0 = host.session(0)
        r, inputs = fetch(p0)
        stage = inputs["stages"][0]
        self.assertEqual((stage["decision_kind"], stage["decline"], stage["count"]), ("discard_from_hand", True, {"min": 0, "max": 2}))
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", []).outcome, D.ACCEPTED)
        self.assertEqual(host.game.state.phase, Phase.MAIN)
        host = host_after_trainer(search_board((H.FIRE, H.WATER), trainer="PMCG5-083"))
        _, inputs = fetch(host.session(0))
        self.assertEqual((inputs["stages"][0]["meaning"], [o["value"] for o in inputs["stages"][0]["options"]]), ("number", [0, 1, 2, 3]))

    def test_decline_shown_but_engine_stops(self):
        """辞退は候補の制約（min 0）では送れるが、エンジンが未裁定で拒否する場面（カツラのギャンブルの 0 枚。PMCG6-076）。候補は受理を保証しない（may_stop_later）。状態は変わらない。"""
        host = host_after_trainer(search_board((H.FIRE, H.WATER), trainer="PMCG6-076"))
        p0 = host.session(0)
        r, inputs = fetch(p0)
        stage = inputs["stages"][0]
        self.assertEqual((stage["decision_kind"], stage["decline"], stage["count"]["min"]), ("discard_from_hand", True, 0))
        self.assertEqual(r["candidates"][0]["processability"], L.MAY_STOP_LATER)
        before = snap(host.game.state)
        result = p0.submit(r["game"], r["revision"], "c1", [])
        self.assertEqual((result.outcome, result.view.category), (D.REJECTED, D.RULING_UNRESOLVED))
        self.assertEqual(snap(host.game.state), before)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o1"]).outcome, D.ACCEPTED)  # 拒否では取っ手は失効しない

    def test_option_that_stops_is_marked_and_not_sent(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        state = host.game.state
        stopped = with_decision(state, context=state.decision.context + (("unresolved_choices", (state.decision.options[0],)),))
        host.replace_game(A.HostedGame(stopped))
        p0 = host.session(0)
        r, inputs = fetch(p0)
        options = inputs["stages"][0]["options"]
        self.assertEqual(options[0]["processability"], L.RULING_UNRESOLVED)  # 候補から消さない
        self.assertEqual([o["processability"] for o in options[1:]], [L.MAY_STOP_LATER] * (len(options) - 1))
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o1", "o2"]).refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o2", "o3"]).outcome, D.ACCEPTED)

    def test_unverified_is_processability_not_disclosure(self):
        """分類のない停止のコードの選択は unverified（処理できるか不明）。入力の情報境界は確かめてあるので、選べるものは返す（2 つの軸は別）。"""
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        state = host.game.state
        context = state.decision.context + (("unresolved_choices", (state.decision.options[0],)), ("unresolved_code", "FUTURE_STOP_FOR_TEST"))
        host.replace_game(A.HostedGame(with_decision(state, context=context)))
        r, inputs = fetch(host.session(0))
        self.assertEqual(r["candidates"][0]["input_disclosure"], L.DISCLOSURE_CONFIRMED)
        options = inputs["stages"][0]["options"]
        self.assertEqual((options[0]["processability"], "card_id" in options[0]), (L.UNVERIFIED, True))

    def test_option_card_not_visible_withholds_the_whole_input(self):
        """実行時の確かめ: 見えないカードが選べるものに来たら、uid だけでなく選べるもの・数・並びも返さない（コードを読んだ範囲では起こらない）。"""
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        state = host.game.state
        hidden = state.players[0].deck[0]
        host.replace_game(A.HostedGame(with_decision(state, options=(hidden,) + state.decision.options[1:])))
        session = host.session(0)
        r, inputs = fetch(session)
        self.assert_withheld(session, r, inputs)

    def assert_withheld(self, session, r, inputs):
        cand = r["candidates"][0]
        self.assertEqual(cand["input_disclosure"], L.DISCLOSURE_UNCONFIRMED)
        self.assertEqual(cand["processability"], L.MAY_STOP_LATER)  # 処理できるかの軸は別（公開してよいかが未確認）
        self.assertEqual(r["coverage"]["withheld_input_candidates"], [cand["id"]])
        self.assertEqual((inputs["withheld"]["code"], inputs["stages"]), (L.INPUT_BOUNDARY_UNCONFIRMED, []))
        text = json.dumps([r, inputs])
        for key in ("options", "count", "card_id", "order", "decline", '"card"'):
            self.assertNotIn(key if key.startswith('"') else f'"{key}"', text)
        for choices in ([], ["o1"], ["o1", "o2"]):
            self.assertEqual(session.check(r["game"], r["revision"], cand["id"], choices)["refusal"]["code"], L.INPUT_BOUNDARY_UNCONFIRMED)
            self.assertEqual(session.submit(r["game"], r["revision"], cand["id"], choices).refusal.code, L.INPUT_BOUNDARY_UNCONFIRMED)

    def test_unconfirmed_kind_withholds_inputs(self):
        """情報境界を確かめていない種類: 入力を返さない。ホストは直接送れる（U7 の外）。v0.162 で全種類を確かめたので、確かめた一覧から 1 つを外して確かめる（補助の作り）。"""
        state = search_board((H.FIRE,), trainer=H.ENERGY_RETRIEVAL)
        state.players[0].discard = [u for u in state.players[0].deck if state.cards[u].card_id == H.WATER]
        state.players[0].deck = [u for u in state.players[0].deck if u not in state.players[0].discard]
        host = host_after_trainer(state)
        p0 = host.session(0)
        r, _ = fetch(p0)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o1"]).outcome, D.ACCEPTED)  # 手札から 1 枚トラッシュ（確かめた種類）
        with mock.patch.object(L, "DISCLOSURE_CONFIRMED_KINDS", L.DISCLOSURE_CONFIRMED_KINDS - {"retrieve_energy"}):
            r, inputs = fetch(p0)
            before = snap(host.game.state)
            self.assert_withheld(p0, r, inputs)
            self.assertEqual(snap(host.game.state), before)
        d = host.game.state.decision
        self.assertEqual(host.game.submit(ResolveDecision(0, d.id, d.options[:1]), submitter=0).outcome, D.ACCEPTED)


class TwinTest(unittest.TestCase):
    """持ち主の知識と公開の情報が同じで、山札とサイドの配分だけが違う双子。取っ手の文字列は比べず、候補・制約・診断と、候補と取っ手の対応を比べる。"""

    def twins(self):
        a = search_board((H.FIRE, H.FIRE, H.PONYTA), deck=(H.WATER, H.SEEL, H.BILL, H.FIRE), prizes=(H.POTION, H.WATER))
        b = search_board((H.FIRE, H.FIRE, H.PONYTA), deck=(H.WATER, H.SEEL, H.POTION, H.FIRE), prizes=(H.BILL, H.WATER))
        for viewer in (0, 1, None):
            self.assertEqual(public_view(a, viewer), public_view(b, viewer))
        self.assertEqual(owned_card_ids(a, 0), owned_card_ids(b, 0))
        return a, b

    def responses(self, host):
        out = []
        for actor in (0, 1):
            session = host.session(actor)
            r = session.candidates()
            item = [without_handles(r)]
            for cand in ("c1", "c9"):
                item.append(session.inputs(r["game"], r["revision"], cand))
                item += [session.check(r["game"], r["revision"], cand, choice) for choice in ([], ["o1"], ["o1", "o2"], ["o1", "o1"], ["o5"])]
                item.append(dataclasses.asdict(session.submit("other", r["revision"], cand, ["o1"])))
            out.append(item)
        return out

    def test_twins_get_the_same_answers_before_the_search(self):
        a, b = self.twins()
        host_a, host_b = L.ActionHost(A.HostedGame(a)), L.ActionHost(A.HostedGame(b))
        self.assertEqual(self.responses(host_a), self.responses(host_b))  # MAIN（番を終える）
        for host, state in ((host_a, a), (host_b, b)):
            host.game.submit(PlayTrainer(0, state.players[0].hand[0]), submitter=0)
        self.assertEqual(self.responses(host_a), self.responses(host_b))  # 手札をトラッシュする決定（検索の前）
        results = []
        for host in (host_a, host_b):
            p0 = host.session(0)
            r = p0.candidates()
            results.append(p0.submit(r["game"], r["revision"], "c1", ["o1", "o2"]).view)
        self.assertEqual(results[0], results[1])
        _, inputs_a = fetch(host_a.session(0))
        _, inputs_b = fetch(host_b.session(0))
        self.assertNotEqual(inputs_a, inputs_b)  # 始まった検索の本人の選択肢は実際の山札による
        self.assertEqual(self.responses(host_a)[1], self.responses(host_b)[1])  # 相手には同じ


class EndTurnTest(unittest.TestCase):
    def poisoned(self):
        return H.build_test_state([
            {"active": H.GROWLITHE, "hand": [H.FIRE], "deck": [H.WATER] * 3, "prizes": [H.WATER, H.WATER]},
            {"active": {"card": H.STARYU, "damage": 30, "poison": 10}, "bench": [H.SEEL], "deck": [H.WATER] * 3, "prizes": [H.WATER, H.WATER]},
        ], turn_number=3)

    def test_end_turn_candidate_and_checkup_decision(self):
        host = L.ActionHost(A.HostedGame(self.poisoned()))
        p0, p1 = host.session(0), host.session(1)
        r = p0.candidates()
        (cand,) = r["candidates"]
        self.assertEqual((cand["kind"], cand["processability"], cand["reasons"]), (L.KIND_END_TURN, L.MAY_STOP_LATER, ["checkup_not_evaluated"]))
        self.assertEqual(r["coverage"]["completeness"], L.PARTIAL)  # 番の操作は番を終えるだけ。全合法手と称さない
        self.assertIn("use_attack", r["coverage"]["not_covered_kinds"])
        self.assertIn("保証しない", cand["guarantees"]["acceptance"])
        self.assertEqual(p1.candidates()["situation"], L.WAITING_FOR_PLAYER)
        self.assertEqual(p0.check(r["game"], r["revision"], "c1", ["o1"])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        result = p0.submit(r["game"], r["revision"], "c1")
        self.assertEqual(result.outcome, D.ACCEPTED)
        state = host.game.state
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)  # ポケモンチェックのどくできぜつ → サイドを取る決定
        r = p0.candidates()
        self.assertEqual(r["candidates"][0]["kind"], L.KIND_TAKE_PRIZE)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o1"]).outcome, D.ACCEPTED)
        self.assertEqual(host.game.state.phase, Phase.PROMOTE_ACTIVE)
        r = p1.candidates()
        self.assertEqual(r["candidates"][0]["kind"], L.KIND_PROMOTE_ACTIVE)
        _, inputs = fetch(p1)
        self.assertEqual(inputs["stages"][0]["meaning"], "pokemon")
        self.assertEqual(p1.submit(r["game"], r["revision"], "c1", ["o1"]).outcome, D.ACCEPTED)

    def test_accepted_answer_then_halt(self):
        """ドライアップの答え（U7 で送る）を受理した結果として途中停止する（送れたことと、そのあとの停止は別）。停止のあとは候補がない。"""
        host, start = L.ActionHost.start(*DRY_DECKS, 0)
        self.assertEqual(start.outcome, D.ACCEPTED)
        last = None
        for _ in range(200):
            if host.game.state.phase is Phase.HALTED:
                break
            command = dry_command(host.game.state)
            last = u7_send(host, command) or host.game.submit(command, submitter=submitter(command))
            self.assertEqual(last.outcome, D.ACCEPTED)
        self.assertEqual(host.game.state.phase, Phase.HALTED)  # 受理した結果として停止した（ドライアップの対象を選ぶ決定は U7 の外でホストが送る場合を含む）
        for actor in (0, 1):
            r = host.session(actor).candidates()
            self.assertEqual((r["situation"], r["candidates"], r["coverage"]["completeness"]), (L.HALTED, [], L.COMPLETE))

    def test_halted_at_start(self):
        host, start = L.ActionHost.start(HALT_DECK, HALT_DECK, 1)
        self.assertEqual((start.outcome, host.game.state.phase), (D.ACCEPTED, Phase.HALTED))
        for actor in (0, 1):
            r = host.session(actor).candidates()
            self.assertEqual((r["situation"], r["candidates"]), (L.HALTED, []))


class PhaseTest(unittest.TestCase):
    def test_setup_phases(self):
        host, _ = L.ActionHost.start(*DECKS, 3)
        for actor in (0, 1):
            r = host.session(actor).candidates()
            self.assertEqual((r["situation"], r["candidates"], r["coverage"]["not_covered_kinds"], r["coverage"]["completeness"]),
                             (L.ACTOR_TO_ACT, [], ["place_starting"], L.PARTIAL))  # 未対応の種類（ゲーム上できないのではない）
        seen = set()
        while host.game.state.phase is not Phase.MAIN:
            state = host.game.state
            for actor in (0, 1):
                r = host.session(actor).candidates()
                seen.add((state.phase, r["situation"]))
                self.assertEqual(r["candidates"], [])
                if state.phase == Phase.SETUP_FIRST_PLAYER:
                    self.assertEqual((r["situation"], r["coverage"]["completeness"]), (L.WAITING_FOR_HOST, L.COMPLETE))
            command = H.trainer_policy_command(state)
            host.game.submit(command, submitter=submitter(command))
        self.assertIn((Phase.SETUP_PLACEMENT, L.WAITING_FOR_PLAYER), seen)
        self.assertIn((Phase.SETUP_FIRST_PLAYER, L.WAITING_FOR_HOST), seen)

    def test_game_over_and_sudden_death(self):
        self.assertEqual(OVER.game.state.phase, Phase.GAME_OVER)
        self.assertEqual(SUDDEN.game.state.phase, Phase.SUDDEN_DEATH)
        for host, situation in ((OVER, L.GAME_OVER), (SUDDEN, L.WAITING_FOR_HOST)):
            for actor in (0, 1):
                r = host.session(actor).candidates()
                self.assertEqual((r["situation"], r["candidates"], r["coverage"]["completeness"]), (situation, [], L.COMPLETE))
        self.assertEqual(SUDDEN.game.submit(StartSuddenDeath()).outcome, D.ACCEPTED)  # ホストの操作（U7-2）はホストが直接送る
        r = SUDDEN.session(0).candidates()
        self.assertEqual(r["coverage"]["not_covered_kinds"], ["place_starting"])

    def test_same_result_as_direct_submission(self):
        direct = drive(0, use_u7=False)
        self.assertEqual(snap(direct.game.state), snap(OVER.game.state))

    def test_three_convention_sets(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                host = drive(5, use_u7=True, conventions=conventions, until=lambda s: s.turn_number >= 6)
                state = host.game.state
                direct = drive(5, use_u7=False, conventions=conventions, until=lambda s: s.turn_number >= 6)
                self.assertEqual(snap(state), snap(direct.game.state))
                r = host.session(state.current_player if state.decision is None else state.decision.player).candidates()
                self.assertEqual(r["situation"], L.ACTOR_TO_ACT)


class HandleTest(unittest.TestCase):
    def setUp(self):
        self.host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        self.p0, self.p1 = self.host.session(0), self.host.session(1)

    def test_accept_invalidates_all_handles(self):
        r0, r1 = self.p0.candidates(), self.p1.candidates()
        self.assertEqual(self.p0.submit(r0["game"], r0["revision"], "c1", ["o1", "o2"]).outcome, D.ACCEPTED)
        self.assertEqual(self.p0.inputs(r0["game"], r0["revision"], "c1")["refusal"]["code"], L.CANDIDATES_STALE)
        self.assertEqual(self.p1.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATES_STALE)
        self.assertEqual(self.host.issued_count(), 0)

    def test_rejection_keeps_other_handles(self):
        r1 = self.p1.candidates()
        r0 = self.p0.candidates()
        state = self.host.game.state
        rejected = self.host.game.submit(EndTurn(1), submitter=1)  # 拒否（決定待ち）
        self.assertEqual(rejected.outcome, D.REJECTED)
        self.p0.submit(r0["game"], r0["revision"], "c1", ["o1"])  # ホストの段の拒否
        self.assertIs(self.host.game.state, state)
        self.assertEqual(self.p1.inputs(r1["game"], r1["revision"], "c1")["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 失効していない（候補がないだけ）
        self.assertEqual(self.p1.check(r1["game"], r1["revision"], "c9", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)
        self.assertEqual(self.p0.submit(r0["game"], r0["revision"], "c1", ["o1", "o2"]).outcome, D.ACCEPTED)

    def test_direct_host_submission_invalidates(self):
        r0 = self.p0.candidates()
        state = self.host.game.state
        self.assertEqual(self.host.game.submit(ResolveDecision(0, state.decision.id, state.decision.options[:2]), submitter=0).outcome, D.ACCEPTED)
        self.assertEqual(self.p0.submit(r0["game"], r0["revision"], "c1", ["o1", "o2"]).refusal.code, L.CANDIDATES_STALE)

    def test_replace_and_restore_start_a_new_generation(self):
        r0 = self.p0.candidates()
        restored = SN.RestoredGame(SN.restore_snapshot(SN.save_snapshot(self.host.game.state)))
        self.host.replace_game(restored)
        self.assertEqual(self.p0.inputs(r0["game"], r0["revision"], "c1")["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        r = self.p0.candidates()
        self.assertNotEqual(r["game"], r0["game"])
        self.assertEqual(self.p0.submit(r["game"], r["revision"], "c1", ["o1", "o2"]).outcome, D.ACCEPTED)  # 復元した対戦（RestoredGame）でも同じ入口
        other = L.ActionHost(A.HostedGame(self.host.game.state))  # ホストの作り直し
        self.assertEqual(other.session(0).inputs(r["game"], r["revision"], "c1")["refusal"]["code"], L.CANDIDATES_WRONG_GAME)

    def test_retention_is_bounded(self):
        first = self.p0.candidates()
        for _ in range(L.MAX_REVISIONS_PER_ACTOR + 3):
            last = self.p0.candidates()
            self.p1.candidates()
        self.assertLessEqual(self.host.issued_count(), 2 * L.MAX_REVISIONS_PER_ACTOR)
        self.assertEqual(self.p0.inputs(first["game"], first["revision"], "c1")["refusal"]["code"], L.CANDIDATES_STALE)
        self.assertNotIn("refusal", self.p0.inputs(last["game"], last["revision"], "c1"))

    def test_handles_do_not_use_the_engine_rng(self):
        state = self.host.game.state
        before = rng_fingerprint(state.rng)
        with mock.patch("random.Random.getrandbits", side_effect=AssertionError("エンジンの乱数")):
            self.p0.candidates()
        self.assertEqual(rng_fingerprint(state.rng), before)

    def test_failed_host_follows_the_stop_contract(self):
        r0 = self.p0.candidates()
        with mock.patch.object(A, "apply_command", side_effect=RuntimeError("テストの内部エラー")):
            result = self.p0.submit(r0["game"], r0["revision"], "c1", ["o1", "o2"])
        self.assertEqual((result.outcome, result.view.status), (D.FAILED, D.UNAVAILABLE))
        with self.assertRaises(A.HostStoppedError):
            self.p0.candidates()


class ThreeDecisionsTest(unittest.TestCase):
    """v0.160 で未確認だった 3 種類（構築盤面。既存のテストの盤面）: 選べるものは場のカードで、決める人に見える。相手の番の決定も含む。"""

    def check_decision(self, pending, kind, decider):
        host = L.ActionHost.from_state(pending)
        state = host.game.state
        d = state.decision
        self.assertEqual((d.kind, d.player), (kind, decider))
        self.assertIn(kind, L.DISCLOSURE_CONFIRMED_KINDS)
        me, other = host.session(decider), host.session(1 - decider)
        r, inputs = fetch(me)
        self.assertEqual((r["situation"], r["candidates"][0]["input_disclosure"]), (L.ACTOR_TO_ACT, L.DISCLOSURE_CONFIRMED))
        stage = inputs["stages"][0]
        self.assertEqual([o["card"] for o in stage["options"]], list(d.options))
        for o in stage["options"]:
            self.assertEqual(o["card_id"], state.cards[o["card"]].card_id)
            self.assertTrue(any(o["card"] in p.energy for pl in state.players for p in pl.in_play()))  # 場についているカード（公開）
        r_other = other.candidates()
        self.assertEqual((r_other["situation"], r_other["candidates"], r_other["empty_reason"]), (L.WAITING_FOR_PLAYER, [], L.EMPTY_NOT_ACTOR))
        self.assertNotIn('"card"', json.dumps(r_other))
        before = snap(state)
        for bad in (["o9"], ["o1", "o1"], [str(d.options[0])]):
            self.assertEqual(me.check(r["game"], r["revision"], "c1", bad)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(snap(state), before)
        executable = [o["id"] for o in stage["options"] if o["processability"] in L.EXECUTABLE]
        direct = A.submit(state, ResolveDecision(decider, d.id, (d.options[int(executable[0][1:]) - 1],)), submitter=decider)
        result = me.submit(r["game"], r["revision"], "c1", executable[:1])
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(decider)))
        if direct.outcome == D.ACCEPTED:
            self.assertEqual(snap(host.game.state), snap(direct.state))
        return stage

    def test_energy_drain_discard(self):
        pending = apply_command(H.with_coin_results(T68.muk_board(), CoinSide.HEADS), UseAttack(0, 0))
        self.assertEqual(pending.current_player, 0)  # 番はプレイヤー 0、決めるのはプレイヤー 1（相手の操作への反応）
        stage = self.check_decision(pending, "energy_drain_discard", 1)
        self.assertEqual(stage["count"], {"min": 1, "max": 1})

    def test_exp_all_energy(self):
        state = T81.ExpAllTest("test_move_one_basic_energy_then_discard")._board()
        stage = self.check_decision(T81.attack(state, 1), "exp_all_energy", 1)
        self.assertEqual((stage["count"], stage["decline"]), ({"min": 0, "max": 1}, True))

    def test_magma_pool_energy(self):
        state = T87.board(T87.magcargo((T87.F,) * 5), bench=(H.CHARMANDER,))
        stage = self.check_decision(T87.retreat(state, 3), "magma_pool_energy", 0)
        self.assertEqual(len(stage["options"]), 2)


class OrderTest(unittest.TestCase):
    def pokedex(self):
        state = search_board((H.FIRE,), deck=(H.WATER, H.SEEL, H.BILL, H.FIRE, H.PONYTA), trainer="PMCG1-082")
        host = host_after_trainer(state)
        p0 = host.session(0)
        r, inputs = fetch(p0)
        stage = inputs["stages"][0]
        self.assertEqual(stage["decision_kind"], "select_look_count")
        three = next(o["id"] for o in stage["options"] if o["value"] == 3)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", [three]).outcome, D.ACCEPTED)
        return host

    def test_order_changes_the_result_and_is_kept(self):
        """ポケモン図鑑の並べかえ（答えの並びが山札の上の新しい並び）: 並びを変えると結果が変わる。U7 は並びを変えず、直接の送信と同じ結果。"""
        finals = []
        for order in (["o1", "o2", "o3"], ["o3", "o1", "o2"]):
            host = self.pokedex()
            state = host.game.state
            p0 = host.session(0)
            r, inputs = fetch(p0)
            stage = inputs["stages"][0]
            self.assertEqual((stage["decision_kind"], stage["order"], stage["order_preserved"]), ("arrange_deck_top", L.ORDER_SIGNIFICANT, True))
            values = tuple(state.decision.options[int(o[1:]) - 1] for o in order)
            direct = A.submit(state, ResolveDecision(0, state.decision.id, values), submitter=0)
            self.assertTrue(p0.check(r["game"], r["revision"], "c1", order)["valid"])
            self.assertEqual(p0.submit(r["game"], r["revision"], "c1", order).outcome, D.ACCEPTED)
            self.assertEqual(snap(host.game.state), snap(direct.state))
            self.assertEqual(tuple(host.game.state.players[0].deck[:3]), values)
            finals.append(snap(host.game.state))
        self.assertNotEqual(finals[0], finals[1])

    def test_unconfirmed_order_is_not_called_unordered(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        _, inputs = fetch(host.session(0))
        self.assertEqual(inputs["stages"][0]["order"], L.ORDER_UNCONFIRMED)  # 手札をトラッシュする 2 枚（確かめていない。順不同と称さない）
        host = self.pokedex()
        state = search_board((H.FIRE, H.WATER), trainer="PMCG5-083")
        _, inputs = fetch(host_after_trainer(state).session(0))
        self.assertEqual(inputs["stages"][0]["order"], L.ORDER_NOT_APPLICABLE)  # 選ぶ数が 1


class CoverageTest(unittest.TestCase):
    def test_reasons_for_empty_candidates(self):
        cases = [(OVER, L.GAME_OVER, L.EMPTY_GAME_ENDED), (SUDDEN, L.WAITING_FOR_HOST, L.EMPTY_HOST_OPERATION)]
        halted, _ = L.ActionHost.start(HALT_DECK, HALT_DECK, 1)
        cases.append((halted, L.HALTED, L.EMPTY_GAME_ENDED))
        for host, situation, reason in cases:
            for actor in (0, 1):
                r = host.session(actor).candidates()
                self.assertEqual((r["situation"], r["empty_reason"], r["coverage"]["scope_kinds"], r["coverage"]["completeness"]), (situation, reason, [], L.COMPLETE))
        setup, _ = L.ActionHost.start(*DECKS, 3)
        r = setup.session(0).candidates()
        self.assertEqual((r["empty_reason"], r["coverage"]["scope_kinds"], r["coverage"]["completeness"]), (L.EMPTY_NOT_COVERED, ["place_starting"], L.PARTIAL))

    def test_decision_answerer_has_priority_over_the_turn(self):
        pending = apply_command(H.with_coin_results(T68.muk_board(), CoinSide.HEADS), UseAttack(0, 0))
        host = L.ActionHost.from_state(pending)
        r1, r0 = host.session(1).candidates(), host.session(0).candidates()
        self.assertEqual((r1["situation"], r1["candidates"][0]["kind"], r1["coverage"]["completeness"]), (L.ACTOR_TO_ACT, L.KIND_ANSWER_DECISION, L.COMPLETE))
        self.assertEqual((r0["situation"], r0["empty_reason"]), (L.WAITING_FOR_PLAYER, L.EMPTY_NOT_ACTOR))  # 番のプレイヤーでも、今は決定の回答者でない

    def test_complete_means_the_listed_scope(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        r = host.session(0).candidates()
        self.assertEqual((r["coverage"]["scope_kinds"], r["coverage"]["completeness"]), ([L.KIND_ANSWER_DECISION], L.COMPLETE))
        self.assertIn("全コマンドの合法手ではない", r["coverage"]["completeness_scope"])


class OwnershipTest(unittest.TestCase):
    def test_returned_values_are_copies(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        p0 = host.session(0)
        r, inputs = fetch(p0)
        expected = copy.deepcopy(p0.inputs(r["game"], r["revision"], "c1"))
        r["candidates"][0]["processability"] = L.NOT_IMPLEMENTED
        r["candidates"][0]["reasons"].append("changed")
        inputs["stages"][0]["options"].clear()
        inputs["stages"][0]["count"]["max"] = 9
        self.assertEqual(p0.inputs(r["game"], r["revision"], "c1"), expected)
        self.assertEqual(p0.check(r["game"], r["revision"], "c1", ["o1", "o2", "o3"])["refusal"]["code"], L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(p0.submit(r["game"], r["revision"], "c1", ["o1", "o2"]).outcome, D.ACCEPTED)

    def test_session_exposes_no_host_or_state(self):
        host = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA)))
        session = host.session(0)
        self.assertFalse(hasattr(session, "__dict__"))
        self.assertEqual({n for n in dir(session) if not n.startswith("__")}, {"_link", "_actor", "actor", "candidates", "inputs", "check", "submit"})
        self.assertFalse(hasattr(session._link, "__dict__"))
        r = session.candidates()
        result = session.submit(r["game"], r["revision"], "c1", ["o1", "o2"])
        self.assertFalse(hasattr(result, "state"))

    def test_from_state_isolates_external_alias(self):
        state = host_after_trainer(search_board((H.FIRE, H.FIRE, H.PONYTA))).game.state
        host = L.ActionHost.from_state(state)
        before = snap(host.game.state)
        state.players[0].hand.clear()  # 外の別名を変えても、ホストの対戦は変わらない（複製した）
        self.assertEqual(snap(host.game.state), before)
        self.assertIsNot(host.game.state, state)
        r = host.session(0).candidates()
        self.assertEqual(host.session(0).submit(r["game"], r["revision"], "c1", ["o1", "o2"]).outcome, D.ACCEPTED)


class DocumentTest(unittest.TestCase):
    def test_document_records_the_scope(self):
        text = (pathlib.Path(__file__).resolve().parent.parent / "docs" / "legal-actions-u7-1.md").read_text(encoding="utf-8")
        for phrase in ("ADOPT-U7-1", "D-U7-DECISION-UID", "全合法手ではない", "MAX_REVISIONS_PER_ACTOR", "U7 全体の部分実装", "unverified"):
            self.assertTrue(phrase in text, phrase)
