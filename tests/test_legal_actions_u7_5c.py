"""v0.169（U7-5c。docs/legal-actions-u7-5c.md）: 手札のトレーナー（PlayTrainer）の候補・入力・検査・送信の回帰テスト。

確かめの種類を分ける:

- 構築盤面（tests.helpers.build_test_state。コインはテストの乱数の仕込み with_coin_results）: 候補・入力・処理可能性・情報境界（秘密の手札・山札・サイドの配分だけを
  変えた双子）・取っ手・不正な入力・状態の不変、受理のあとの決定（対象・費用・検索・錯乱ジム・［ちえくらべ］・サイキックコントロール）、どうぐ・スタジアム・化石／人形・番を終えるカード
- 補助関数の確かめ: check_play_trainer とコマンドの処理の拒否の一致、使うための条件の分類（PLAYABLE_NOT_EVALUATED・PLAYABLE_BOARD_TRIALS）と設計の走査の一致、
  条件を差し替えた盤面での処理可能性の区分（技術的制限・effects.py の外の条件）
- new_game からの合法な操作の列（固定の seed。3 つの規約集合）: 準備を U7 で終え、トレーナーを U7 で使い、受理のあとの決定に U7 で答える。直接の列と同じ状態。
  完全な再現用記録の収集・U4 の再実行・閲覧用記録の構造

停止コードの文字列はテストの中に書かない（区分・ホストの段のコード・エンジンの例外の型で確かめる）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest
from unittest import mock

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import effects as E
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import PlayTrainer, ResolveDecision
from kyuura_engine.decisions import ACCEPT_REQUEST, USE_DISCARD_TRAINER
from kyuura_engine.engine import apply_command, check_play_trainer
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.state import Phase
from kyuura_engine.view_record import FORBIDDEN_KEYS
from tests import helpers as H
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
from tests.test_legal_actions_u7_5ab import DOLL_DECK, DOLL_SEED

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = {"contract": "kyuura-client-api", "format": 1}
HD, TL = CoinSide.HEADS, CoinSide.TAILS
SLOWKING, SLOWPOKE, PSYCHIC = "neo1-049", "neo1-045", "PMCG1-101"
QUIZ3, SWAP = "PMCG6-082", "PR1-027"  # カツラのクイズ その3（BlainesQuiz）・とりかえっこプリーズ（SwapPleaseTrainer）。どちらも PLAYABLE_NOT_EVALUATED


def uid(state, card_id, player=0, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def board(hand, *, active=None, bench=(H.RATTATA,), deck=None, prizes=None, discard=(), them=None, effects=None):
    """プレイヤー 0 の番（5 番）。相手（1）のバトル場はヒトカゲ、ベンチにコラッタ。"""
    me = {"active": active or {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": list(bench), "hand": list(hand), "deck": list(deck or [H.FIRE] * 8),
          "prizes": list(prizes or [H.FIRE] * 2), "discard": list(discard)}
    them = them or {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": [H.WATER], "deck": [H.FIRE] * 8}
    return H.build_test_state([me, them], turn_number=5, **({"effects": effects} if effects else {}))


def slowking_side(**extra):
    return {"active": {"card": SLOWKING, "energy": [PSYCHIC] * 3, "evolved_from": SLOWPOKE}, "bench": [H.RATTATA], "hand": [], "deck": [H.FIRE] * 8, **extra}


def trainer_stage(state, actor=0):
    _r, c, inputs = inputs_of(host_of(state).session(actor), L.KIND_PLAY_TRAINER)
    return c, (None if inputs is None else inputs["stages"][0])


def option_for(stage, card):
    return next(o["id"] for o in stage["options"] if o["card"] == card)


def via_u7(state, card, *, actor=0):
    host = host_of(state.clone())
    session = host.session(actor)
    r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
    return host, session.submit(r["game"], r["revision"], c["id"], [option_for(inputs["stages"][0], card)])


def via_direct(state, command):
    game = A.HostedGame(state.clone())
    return game, game.submit(command, submitter=command.player)


def answer_u7(host, choose):
    """今の決定に、決める人の U7 の answer_decision の候補で答える（``choose`` は段から選ぶものの番号の並びを作る）。"""
    session = host.session(host.game.state.decision.player)
    r = session.candidates()
    c = cand(r, L.KIND_ANSWER_DECISION)
    stage = session.inputs(r["game"], r["revision"], c["id"])["stages"][0]
    return session.submit(r["game"], r["revision"], c["id"], choose(stage))


class Same:
    def assert_same_as_direct(self, state, card):
        host, result = via_u7(state, card)
        game, direct = via_direct(state, PlayTrainer(0, card))
        self.assertEqual((result.outcome, result.view), (direct.outcome, direct.view_for(0)))
        self.assertEqual(snap(host.game.state), snap(game.state))
        return host, game, result


class MappingTest(unittest.TestCase):
    """対応表（docs/legal-actions-u7-5c.md 2 章）: play_trainer は既存の PlayTrainer だけ。宣言の入力は card だけ。ほかの入口は対応しない種類のまま（main は partial）。"""

    def test_kind_command_fields_and_coverage(self):
        self.assertEqual([f.name for f in dataclasses.fields(PlayTrainer)], ["player", "card"])  # player は主体（取っ手）、card だけが宣言の入力
        self.assertIn(L.KIND_PLAY_TRAINER, L.IMPLEMENTED_KINDS)
        r = host_of(board([H.BILL])).session(0).candidates()
        cov = r["coverage"]
        self.assertEqual(cov["completeness"], L.PARTIAL)
        self.assertEqual(cov["scope_kinds"], list(L.MAIN_KINDS))
        self.assertEqual(cov["not_covered_kinds"], [])  # v0.170・v0.171（U7-5d・U7-5e）: use_stadium・use_power は対応した種類（v0.172（U7-5f）: check_face_up_deck も評価した種類（表示だけ。display_only_kinds）。未対応の種類はない）
        kinds = [c["kind"] for c in r["candidates"]]
        self.assertEqual(kinds, sorted(kinds, key=L.MAIN_KINDS.index))
        c = cand(r, L.KIND_PLAY_TRAINER)
        self.assertEqual((c["processability"], c["input_disclosure"], c["input_stages"]), (L.MAY_STOP_LATER, L.DISCLOSURE_CONFIRMED, [{"stage": 1, "input": L.INPUT_CHOOSE_OPTION}]))
        self.assertIn("supported にしない", c["guarantees"]["supported_scope"])

    def test_absent_when_no_trainer_or_not_the_turn(self):
        self.assertIsNone(cand(host_of(board([H.FIRE, H.RATTATA])).session(0).candidates(), L.KIND_PLAY_TRAINER))  # 手札にトレーナーがない（ゲーム上できない）
        r = host_of(board([H.BILL])).session(1).candidates()
        self.assertEqual((r["situation"], r["candidates"]), (L.WAITING_FOR_PLAYER, []))  # 番でない主体には、相手の手札の候補を作らない

    def test_trainer_lock_hides_the_kind(self):
        # ［アレルギーかふん］（わるいラフレシア）がはたらく盤面: 誰もトレーナーを使えない（ゲーム上の禁止なので候補を作らない）
        vileplume = {"active": {"card": H.DARK_VILEPLUME, "energy": [H.GRASS], "evolved_from": [H.ROCKET_ODDISH, H.DARK_GLOOM],
                                "evolved_turn": 4}, "bench": [H.RATTATA], "hand": [],
                     "deck": [H.FIRE] * 8}
        state = board([H.BILL, H.POTION], them=vileplume)
        with self.assertRaises(IllegalActionError):
            apply_command(state, PlayTrainer(0, uid(state, H.BILL)))
        self.assertIsNone(trainer_stage(state)[0])


class CheckFunctionTest(unittest.TestCase):
    """check_play_trainer が、コマンドの処理と同じ拒否（型・コード）になる（補助関数の確かめ）。"""

    def test_same_codes_as_commands(self):
        states = [board([H.BILL, H.POTION, H.FIRE, H.SWITCH]), board([H.SWITCH], bench=()), board([H.SUPER_POTION], effects=H.NO_SUPER_POTION_EFFECTS),
                  board([QUIZ3, SWAP])]
        for state in states:
            for actor in (0, 1):
                for card in [u for side in state.players for u in side.hand] + [999]:
                    cmd = PlayTrainer(actor, card)
                    expected = found = None
                    try:
                        check_play_trainer(state, cmd)
                    except (IllegalActionError, UnsupportedError) as error:
                        expected = (type(error), error.code)
                    try:
                        apply_command(state, cmd)
                    except (IllegalActionError, UnsupportedError) as error:
                        found = (type(error), error.code)
                    self.assertEqual(found, expected, cmd)

    def test_skipping_the_use_condition_skips_only_that_check(self):
        state = board([SWAP])  # 手札にほかのカードがない: とりかえっこプリーズの使うための条件で拒否
        with self.assertRaises(IllegalActionError):
            check_play_trainer(state, PlayTrainer(0, uid(state, SWAP)))
        check_play_trainer(state, PlayTrainer(0, uid(state, SWAP)), use_condition=False)
        with self.assertRaises(IllegalActionError):
            check_play_trainer(state, PlayTrainer(1, uid(state, SWAP)), use_condition=False)  # 番の確かめは残る


class NormalTrainerTest(Same, unittest.TestCase):
    def test_bill_same_as_direct(self):
        state = board([H.BILL, H.FIRE])
        host, _game, result = self.assert_same_as_direct(state, uid(state, H.BILL))
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertIn(uid(state, H.BILL), host.game.state.players[0].discard)  # 使い終えたらトラッシュ（既存の扱い）

    def test_target_decision_after_acceptance(self):
        state = board([H.POTION], active={"card": H.CHARMANDER, "energy": [H.FIRE], "damage": 20})
        potion = uid(state, H.POTION)
        host, game, _ = self.assert_same_as_direct(state, potion)
        self.assertEqual((host.game.state.trainer_in_use.card, host.game.state.phase), (potion, Phase.DECISION))  # 決定を待つ間は使用中の場所
        self.assertNotIn(potion, host.game.state.players[0].hand)
        sent = answer_u7(host, lambda stage: [stage["options"][0]["id"]])
        target = game.state.decision
        direct = game.submit(ResolveDecision(0, target.id, (target.options[0],)), submitter=0)
        self.assertEqual((sent.outcome, direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_search_and_cost_decisions_after_acceptance(self):
        for trainer, hand in ((H.ENERGY_SEARCH, [H.ENERGY_SEARCH]), (H.COMPUTER_SEARCH, [H.COMPUTER_SEARCH, H.FIRE, H.WATER])):
            with self.subTest(trainer=trainer):
                state = board(hand, deck=[H.FIRE, H.WATER, H.RATTATA, H.FIRE])
                host, game, _ = self.assert_same_as_direct(state, uid(state, trainer))
                self.assertIsNotNone(host.game.state.decision)
                for _ in range(3):  # 費用（手札から 2 枚）・山札の検索に U7 で答える。直接の答えと同じ
                    d = game.state.decision
                    if d is None:
                        break
                    picked = d.options[:d.min_choices or 1]
                    count = len(picked)
                    sent = answer_u7(host, lambda stage, n=count: [o["id"] for o in stage["options"][:n]])
                    self.assertEqual((sent.outcome, game.submit(ResolveDecision(d.player, d.id, tuple(picked)), submitter=d.player).outcome), (D.ACCEPTED, D.ACCEPTED))
                    self.assertEqual(snap(host.game.state), snap(game.state))


class StopsTest(unittest.TestCase):
    """未裁定・未実装・技術的制限: 選べるものとして示し、実行できない区分にする（ゲーム上の禁止とは別。送る前に CANDIDATE_NOT_EXECUTABLE）。"""

    def assert_blocked(self, state, card, processability):
        host = host_of(state)
        session = host.session(0)
        r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
        option = next(o for o in inputs["stages"][0]["options"] if o["card"] == card)
        self.assertEqual((option["processability"], option["eligible"]), (processability, False))
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], [option["id"]])["refusal"]["code"], L.CANDIDATE_NOT_EXECUTABLE)
        before = snap(host.game.state)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [option["id"]]).refusal.code, L.CANDIDATE_NOT_EXECUTABLE)
        self.assertEqual(snap(host.game.state), before)

    def test_unregistered_is_not_implemented(self):
        state = board([H.SUPER_POTION], effects=H.NO_SUPER_POTION_EFFECTS)
        self.assert_blocked(state, uid(state, H.SUPER_POTION), L.NOT_IMPLEMENTED)

    def test_unresolved_use_condition(self):
        state = board([H.SWITCH, H.BILL], bench=())
        self.assert_blocked(state, uid(state, H.SWITCH), L.RULING_UNRESOLVED)
        self.assertEqual(trainer_stage(state)[0]["processability"], L.MAY_STOP_LATER)  # 候補の区分は、いちばん進めやすい選べるもの（マサキ）

    def test_mind_games_with_chaos_gym_is_mg1(self):
        state = board([H.CHAOS_GYM, H.BILL], them=slowking_side())
        state = apply_command(state, PlayTrainer(0, uid(state, H.CHAOS_GYM)))  # 相手の［ちえくらべ］の決定（使わない）→ 錯乱ジムが場に出る
        state = apply_command(state, ResolveDecision(1, state.decision.id, ()))
        self.assertIsNotNone(state.stadium)
        self.assert_blocked(state, uid(state, H.BILL), L.RULING_UNRESOLVED)

    def test_technical_limit_category(self):
        """補助の確かめ: effects.py の型の使うための条件が技術的制限のコードで止めると、technical_limit（条件を差し替えた盤面。カードの挙動の確かめではない）。"""
        code = next(c for c, e in D.default_catalog().codes.items() if e.category == D.TECHNICAL_LIMIT)

        def stop(self, state, use):
            raise UnsupportedError(code, "test")

        state = board([H.BILL])
        with mock.patch.object(E.DrawCards, "check_playable", stop):
            self.assert_blocked(state, uid(state, H.BILL), L.TECHNICAL_LIMIT)

    def test_condition_defined_outside_effects_is_not_called(self):
        """補助の確かめ: effects.py の外で定義した使うための条件は、候補の作成で呼ばない（unverified。送信ではエンジンが呼ぶ）。"""
        called = []

        @dataclasses.dataclass(frozen=True)
        class Outside(E.DrawCards):
            def check_playable(self, state, use):
                called.append(use.card)

        effects = E.DEFAULT_EFFECTS.with_trainers("test-outside", {H.BILL: dataclasses.replace(E.DEFAULT_EFFECTS.trainer_entry(H.BILL), effect=Outside(2))})
        state = board([H.BILL], effects=effects)
        _c, stage = trainer_stage(state)
        self.assertEqual((stage["options"][0]["processability"], called), (L.UNVERIFIED, []))
        self.assertIn(L.REASON_USE_CONDITION, stage["options"][0]["reasons"])
        _host, result = via_u7(state, uid(state, H.BILL))
        self.assertEqual((result.outcome, called), (D.ACCEPTED, [uid(state, H.BILL)]))


class UseConditionTest(unittest.TestCase):
    """カードごとの使うための条件（docs/legal-actions-u7-5c.md 4 章）: A・A-own は呼ぶ、場だけを試す 6 は呼ぶ、山札から引いて試す 5 は呼ばない。"""

    def test_classification_matches_the_design_scan(self):
        spec = json.loads((ROOT / "docs" / "legal-actions-u7-5-design.json").read_text(encoding="utf-8"))
        trials = set(spec["scan"]["check_playable"]["trials"])
        # v0.176（PT-5e）: 山札から引いて試す 5 つは PLAYABLE_FACE_UP_PREFIX_TRIALS（呼ぶ。おもての山札の並びの不変条件が成り立つ状態だけ）。PLAYABLE_NOT_EVALUATED は空
        self.assertEqual(L.PLAYABLE_NOT_EVALUATED, frozenset())
        self.assertEqual(L.PLAYABLE_FACE_UP_PREFIX_TRIALS | L.PLAYABLE_BOARD_TRIALS, trials)
        self.assertFalse(L.PLAYABLE_FACE_UP_PREFIX_TRIALS & L.PLAYABLE_BOARD_TRIALS)
        for name in trials:
            self.assertIn("check_playable", vars(getattr(E, name)), name)  # 条件を定義した型の名前（継承した型は定義した型で引く）

    def test_draw_trials_are_called_by_queries(self):
        """v0.176（PT-5e）: 山札から引いて試す条件も、候補の作成で呼ぶ（v0.175 までは呼ばず unverified）。check は候補の記録を使い、条件を呼び直さない。"""
        for card, cls in ((QUIZ3, E.BlainesQuiz), (SWAP, E.SwapPleaseTrainer)):
            with self.subTest(card=card):
                state = board([card, H.RATTATA])
                calls = []
                original = cls.check_playable

                def recorded(self, state, use, original=original):
                    calls.append(use.card)
                    return original(self, state, use)

                host = host_of(state)
                session = host.session(0)
                before = snap(host.game.state)
                with mock.patch.object(cls, "check_playable", recorded):
                    r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
                    built = len(calls)
                    option = inputs["stages"][0]["options"][0]
                    self.assertTrue(session.check(r["game"], r["revision"], c["id"], [option["id"]])["valid"])
                self.assertEqual((built, len(calls)), (1, 1))
                self.assertEqual((option["processability"], option["eligible"]), (L.MAY_STOP_LATER, True))
                self.assertEqual(sorted(option["reasons"]), sorted([L.REASON_PREFLIGHT, L.REASON_CONTINUATION]))
                self.assertEqual(snap(host.game.state), before)

    def test_unusable_draw_trial_is_not_offered(self):
        """v0.176（PT-5e）: 手札にほかのカードがないとりかえっこプリーズは、使うための条件でゲーム上使えない（Illegal）ので選べるものに出さない（v0.175 までは unverified で示し、
        送るとエンジンが本人にだけ拒否した）。直接のコマンドは同じコードで拒否する（意図した API 上の差: 送る前に候補にない）。"""
        state = board([SWAP])
        hub = ClientHub.from_state(state.clone())
        me = hub.player(0)
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        self.assertIsNone(cand(r, L.KIND_PLAY_TRAINER))
        self.assertEqual([hub.take_updates(a) for a in (0, 1, "spectator", "host")], [[], [], [], []])
        with self.assertRaises(IllegalActionError):
            apply_command(state, PlayTrainer(0, uid(state, SWAP)))

    def test_board_trial_is_evaluated(self):
        state = board([H.SWITCH])
        _c, stage = trainer_stage(state)
        self.assertEqual(stage["options"][0]["processability"], L.MAY_STOP_LATER)  # ポケモンいれかえ（PLAYABLE_BOARD_TRIALS）は呼ぶ
        _host, result = via_u7(state, uid(state, H.SWITCH))
        self.assertEqual(result.outcome, D.ACCEPTED)

    def test_owner_knowledge_twins(self):
        """A-own（持ち主の知識の関数）: 山札とサイドの配分だけを変えた双子で、候補・入力・不正な入力への応答が同じ（実際の配分を読まない）。"""
        twins = [board([H.ENERGY_SEARCH, H.COMPUTER_SEARCH, H.FIRE, H.WATER], deck=deck, prizes=prizes)
                 for deck, prizes in (([H.WATER] * 7 + [H.FIRE], [H.RATTATA, H.RATTATA]), ([H.WATER] * 6 + [H.RATTATA, H.RATTATA], [H.FIRE, H.WATER]))]
        self.assertEqual(*[responses(s, (0, 1, None)) for s in twins])


def responses(state, viewers, actor=0):
    """本人の候補・入力・入力の検査の応答（取っ手を除く）と、``viewers``（秘密を知らない閲覧者）の観測とログ。"""
    host = host_of(state)
    session = host.session(actor)
    r = session.candidates()
    out = [without_handles(r)]
    for c in r["candidates"]:
        out.append(session.inputs(r["game"], r["revision"], c["id"]))
        for choices in ([], ["o1"], ["o2"], ["o1", "o2"], ["o9"], [1]):
            out.append(session.check(r["game"], r["revision"], c["id"], choices))
    for viewer in viewers:
        out += [observe(host.game.state, viewer), visible_log(host.game.state, viewer)]
    return out


class TwinTest(unittest.TestCase):
    """秘密の配分を変えた双子: 本人の候補・件数・並び・制約・理由・不正な入力への応答、相手・観戦者に見える値が同じ。"""

    def test_opponent_hand_and_deck(self):
        hand = [H.BILL, H.POKEMON_TRADER, H.GOOD_MANNERS, H.POKEMON_BREEDER, H.RATTATA, H.CHARIZARD]
        them = [{"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": h, "deck": d}
                for h, d in (([H.WATER, H.CHARMANDER], [H.FIRE] * 8), ([H.CHARIZARD, H.WATER], [H.WATER] * 4 + [H.FIRE] * 4))]
        self.assertEqual(*[responses(board(hand, them=t), (0, None)) for t in them])  # 相手の手札・山札は本人（0）と観戦者に見えない

    def test_own_deck_order(self):
        self.assertEqual(*[responses(board([H.BILL, QUIZ3, SWAP, H.ENERGY_SEARCH, H.RATTATA], deck=d), (0, 1, None))
                           for d in ([H.FIRE] * 4 + [H.WATER] * 4, [H.WATER] * 4 + [H.FIRE] * 4)])  # 山札の並びは誰にも見えない


class SpecialPathTest(Same, unittest.TestCase):
    def test_stadium_from_hand_then_chaos_gym_borrow(self):
        """錯乱ジムを U7 で場に出し、ポケモン交換おじさんのコインが「うら」: 相手に ACCEPT_REQUEST。使えない相手の「使う」はエンジンの拒否（相手にだけ）、「使わない」は受理。"""
        state = H.with_coin_results(board([H.CHAOS_GYM, H.POKEMON_TRADER, H.RATTATA]), TL)  # コインの結果（スタジアムを出すときは投げない。交換おじさんのコイン）
        host, _game, _ = self.assert_same_as_direct(state, uid(state, H.CHAOS_GYM))
        self.assertEqual(host.game.state.stadium.card, uid(state, H.CHAOS_GYM))
        trader = uid(state, H.POKEMON_TRADER)
        session = host.session(0)
        r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], [option_for(inputs["stages"][0], trader)]).outcome, D.ACCEPTED)
        d = host.game.state.decision
        self.assertEqual((d.kind, d.player), (ACCEPT_REQUEST, 1))
        self.assertEqual(host.session(0).candidates()["situation"], L.WAITING_FOR_PLAYER)
        before = snap(host.game.state)
        self.assertEqual(answer_u7(host, lambda stage: [stage["options"][0]["id"]]).outcome, D.REJECTED)  # 相手の手札にポケモンがない
        self.assertEqual(snap(host.game.state), before)
        self.assertEqual(answer_u7(host, lambda stage: []).outcome, D.ACCEPTED)
        self.assertIn(trader, host.game.state.players[0].discard)

    def test_mind_games_answer_by_opponent(self):
        state = board([H.BILL, H.FIRE], them=slowking_side())
        host, game, _ = self.assert_same_as_direct(state, uid(state, H.BILL))
        d = host.game.state.decision
        self.assertEqual(d.player, 1)  # ［ちえくらべ］を使うかは相手が決める（任意）
        sent = answer_u7(host, lambda stage: [])
        direct = game.submit(ResolveDecision(1, d.id, ()), submitter=1)
        self.assertEqual((sent.outcome, direct.outcome), (D.ACCEPTED, D.ACCEPTED))
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_psychic_control_uses_existing_decision(self):
        them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "hand": [H.WATER], "deck": [H.FIRE] * 8, "discard": [H.POTION, H.SUPER_ENERGY_REMOVAL]}
        state = H.with_coin_results(board([H.SABRINAS_PSYCHIC_CONTROL], active={"card": H.CHARMANDER, "energy": [], "damage": 20}, them=them), HD)
        host, game, _ = self.assert_same_as_direct(state, uid(state, H.SABRINAS_PSYCHIC_CONTROL))
        d = host.game.state.decision
        self.assertEqual(d.kind, USE_DISCARD_TRAINER)
        removal, potion = uid(state, H.SUPER_ENERGY_REMOVAL, 1, "discard"), uid(state, H.POTION, 1, "discard")
        self.assertEqual(set(d.options), {removal, potion})  # F-8: 選べるものは公開の情報だけで作る（条件を満たせない超エネルギーリムーブも残る）
        before = snap(host.game.state)
        self.assertEqual(answer_u7(host, lambda stage: [next(o["id"] for o in stage["options"] if o["card"] == removal)]).outcome, D.REJECTED)
        self.assertEqual(snap(host.game.state), before)
        self.assertEqual(answer_u7(host, lambda stage: [next(o["id"] for o in stage["options"] if o["card"] == potion)]).outcome, D.ACCEPTED)
        self.assertEqual(game.submit(ResolveDecision(0, d.id, (potion,)), submitter=0).outcome, D.ACCEPTED)
        self.assertEqual(snap(host.game.state), snap(game.state))

    def test_tools_stadium_fossil_doll(self):
        for card in (H.PLUSPOWER, H.DEFENDER, H.CLEFAIRY_DOLL, H.MYSTERIOUS_FOSSIL, H.CHAOS_GYM):
            with self.subTest(card=card):
                state = board([card, H.FIRE])
                _host, _game, result = self.assert_same_as_direct(state, uid(state, card))
                self.assertEqual(result.outcome, D.ACCEPTED)

    def test_trainer_that_ends_the_turn(self):
        state = H.with_coin_results(board([H.ROCKET_GRUNT, H.FIRE]), TL, TL)
        host, _game, result = self.assert_same_as_direct(state, uid(state, H.ROCKET_GRUNT))
        self.assertEqual(result.outcome, D.ACCEPTED)
        self.assertNotEqual((host.game.state.current_player, host.game.state.phase), (0, Phase.MAIN))  # 「うら」で番が終わる（ポケモンチェック・相手の番へ）
        self.assertIn(uid(state, H.ROCKET_GRUNT), host.game.state.players[0].discard)


class SessionContractTest(unittest.TestCase):
    STATES = (lambda: board([H.BILL, H.POTION, QUIZ3, H.SWITCH]), lambda: board([H.SUPER_POTION], effects=H.NO_SUPER_POTION_EFFECTS),
              lambda: board([H.BILL, H.CHAOS_GYM], them=slowking_side()))

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
        host = host_of(board([H.BILL, H.FIRE]))
        session, other = host.session(0), host.session(1)
        r, c, _ = inputs_of(session, L.KIND_PLAY_TRAINER)
        for choices in ([], ["o9"], ["o1", "o1"], ["o1", "o2"], [0], "o1", None):
            self.assertEqual(session.check(r["game"], r["revision"], c["id"], choices)["refusal"]["code"], L.CANDIDATE_INPUT_INVALID, choices)
        self.assertEqual(other.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_ACTOR)
        self.assertEqual(session.check("other", r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_WRONG_GAME)
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o9"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        r1 = other.candidates()  # 相手の取っ手（候補はない）は、本人の拒否で失効しない
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1", "o1"]).refusal.code, L.CANDIDATE_INPUT_INVALID)
        self.assertEqual(other.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATE_UNKNOWN)  # 失効していない（知らない候補の番号）
        self.assertTrue(session.check(r["game"], r["revision"], c["id"], ["o1"])["valid"])
        self.assertEqual(session.submit(r["game"], r["revision"], c["id"], ["o1"]).outcome, D.ACCEPTED)
        self.assertEqual(session.check(r["game"], r["revision"], c["id"], ["o1"])["refusal"]["code"], L.CANDIDATES_STALE)  # 受理で失効
        self.assertEqual(other.check(r1["game"], r1["revision"], "c1", [])["refusal"]["code"], L.CANDIDATES_STALE)

    def test_no_verifier_values(self):
        for make in self.STATES:
            session = host_of(make()).session(0)
            r = session.candidates()
            payload = [r] + [session.inputs(r["game"], r["revision"], c["id"]) for c in r["candidates"]]
            self.assertFalse(set(keys(payload)) & (FORBIDDEN_KEYS - {"operation_id"}))
            self.assertNotIn("seed", json.dumps(payload))


class ClientApiTest(unittest.TestCase):
    def test_trainer_through_client_api(self):
        state = board([H.BILL, H.FIRE])
        bill = uid(state, H.BILL)
        hub = ClientHub.from_state(state.clone())
        me, spectator = hub.player(0), hub.spectator()
        self.assertFalse(spectator.handle({**CONTRACT, "type": "candidates"}).get("ok", False))  # 観戦者には候補の入口がない
        self.assertEqual(hub.player(1).handle({**CONTRACT, "type": "candidates"})["response"]["candidates"], [])
        r = me.handle({**CONTRACT, "type": "candidates"})["response"]
        c = cand(r, L.KIND_PLAY_TRAINER)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stage = me.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"][0]
        choices = [option_for(stage, bill)]
        self.assertTrue(me.handle({**CONTRACT, "type": "check", **fields, "choices": choices})["response"]["valid"])
        bad = me.handle({**CONTRACT, "type": "submit", **fields, "choices": ["o9"]})
        self.assertEqual((bad["outcome"], bad["refusal"]["code"]), (L.REFUSED, L.CANDIDATE_INPUT_INVALID))
        self.assertEqual([hub.take_updates(a) for a in (1, "spectator")], [[], []])  # 断りは相手・観戦者へ知らせない
        sent = me.handle({**CONTRACT, "type": "submit", **fields, "choices": choices})
        self.assertEqual((sent["outcome"], sent["refetch_required"]), (D.ACCEPTED, True))
        game, _ = via_direct(state, PlayTrainer(0, bill))
        updates = {a: hub.take_updates(a) for a in (1, "spectator")}
        self.assertEqual(updates["spectator"][-1]["observation"], observe(game.state, None))
        self.assertEqual(updates[1][-1]["observation"], observe(game.state, 1))
        text = json.dumps(sent, ensure_ascii=False)
        self.assertNotIn("Traceback", text)


# new_game からの合法な操作の列（事前に固定した seed）
CHAOS_DECK = [c for c in (H.CHAOS_GYM, H.POKEMON_TRADER, H.CHARMANDER, H.CHARMELEON, H.VULPIX, H.PONYTA, H.GROWLITHE, H.MAGMAR) for _ in range(4)] + [H.FIRE] * 28
CHAOS_SEED = 16  # T-F1（tests/test_chaos_gym_borrow_t_f1.py）と同じ列: 先攻の最初の番に錯乱ジム・交換おじさん・ポケモン。交換おじさんのコインが「うら」


def play_with_u7(host, card):
    session = host.session(0)
    r, c, inputs = inputs_of(session, L.KIND_PLAY_TRAINER)
    return session.submit(r["game"], r["revision"], c["id"], [option_for(inputs["stages"][0], card)])


class ConnectionTest(unittest.TestCase):
    """準備からトレーナーの使用・決定の答えまでを U7 で進め、直接の列と同じ状態。3 つの規約集合。"""

    def assert_same_direct(self, start, recording, host):
        direct = A.HostedGame(start.state.clone())
        for command, submitter in recording.sent:
            self.assertEqual(direct.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
        self.assertEqual(snap(direct.state), snap(host.game.state))

    def test_doll_from_new_game(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(DOLL_DECK, DOLL_DECK, DOLL_SEED, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                doll = uid(host.game.state, H.CLEFAIRY_DOLL)
                self.assertEqual(play_with_u7(host, doll).outcome, D.ACCEPTED)  # 人形はポケモンとして場に出る
                self.assertIn(doll, [q.card for q in host.game.state.players[0].in_play()])
                r = host.session(0).candidates()
                self.assertEqual(host.session(0).submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"], []).outcome, D.ACCEPTED)
                self.assertTrue(any(isinstance(command, PlayTrainer) for command, _ in recording.sent))
                self.assert_same_direct(start, recording, host)

    def test_chaos_gym_from_new_game_record_and_replay(self):
        from kyuura_engine import replay_run, view_record
        from kyuura_engine.replay_record import ReplayCollector

        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(CHAOS_DECK, CONNECT_DECK, CHAOS_SEED, **options)
                recording = Recording(start.state.clone())
                host = L.ActionHost(recording)
                setup_with_u7(host)
                self.assertEqual(play_with_u7(host, uid(host.game.state, H.CHAOS_GYM)).outcome, D.ACCEPTED)
                self.assertEqual(play_with_u7(host, uid(host.game.state, H.POKEMON_TRADER)).outcome, D.ACCEPTED)
                d = host.game.state.decision
                self.assertEqual((d.kind, d.player), (ACCEPT_REQUEST, 1))
                self.assertEqual(answer_u7(host, lambda stage: []).outcome, D.ACCEPTED)  # 相手は U7 の answer_decision で「使わない」
                r = host.session(0).candidates()
                self.assertEqual(host.session(0).submit(r["game"], r["revision"], cand(r, L.KIND_END_TURN)["id"], []).outcome, D.ACCEPTED)
                self.assert_same_direct(start, recording, host)
                collector, _ = ReplayCollector.start(CHAOS_DECK, CONNECT_DECK, CHAOS_SEED, include_git=False, **options)
                for command, submitter in recording.sent:
                    self.assertEqual(collector.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                record = collector.close()
                report = replay_run.replay(record)
                self.assertEqual(report.status, replay_run.SUCCEEDED, report.mismatch)
                view_report, views = view_record.view_records_from_replay(record)
                self.assertEqual(view_report.status, replay_run.SUCCEEDED)
                for viewer, rec in views.items():
                    self.assertEqual(view_record.validate_view_record(rec).problems, (), viewer)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = (ROOT / "docs" / "legal-actions-u7-5c.md").read_text(encoding="utf-8")
        for phrase in ("PlayTrainer", "check_play_trainer", "play_trainer", "PLAYABLE_NOT_EVALUATED", "PLAYABLE_BOARD_TRIALS", "use_condition_not_evaluated",
                       "may_stop_later", "unverified", "partial", "kyuura-client-api", "MG1", "F-8", "F-9", "R-1", "R-2", "U7-5d"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
