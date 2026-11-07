"""T-F1（v0.168。docs/chaos-gym-borrow-t-f1.md）: 錯乱ジムの「うら」で、相手がかわりに使えるかの確かめ（と、同じ確かめを使うナツメのサイキックコントロールの選べるもの）が、
相手・観戦者に見えない手札・山札の中身を読み、その結果が公開の分岐（決定の有無・選べるものの数・公開のログ）に出ていた情報漏れの回帰テスト。

確かめの種類を分ける:

- 構築盤面（tests.helpers.build_test_state。コインはテストの乱数の仕込み with_coin_results）: 双子（秘密の手札・山札とサイドの配分だけが違う）・承諾・辞退・
  使えないときの承諾の拒否・公開の情報だけで使えないカード・保存と復元・3 つの規約集合・client_api
- new_game からの合法な操作の列（事前に固定した seed）: 完全な再現用記録の収集・U4 の再実行・閲覧用記録の情報境界

停止コードの文字列は書かない（拒否の型・決定の有無・公開のログで確かめる）。
"""

from __future__ import annotations

import unittest

from kyuura_engine import adapter as A
from kyuura_engine import diagnostics as D
from kyuura_engine import legal_actions as L
from kyuura_engine.client_api import ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.commands import PlayTrainer, ResolveDecision
from kyuura_engine.decisions import ACCEPT_REQUEST, USE_DISCARD_TRAINER
from kyuura_engine.engine import apply_command
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.snapshot import (
    dumps_snapshot,
    loads_snapshot,
    restore_snapshot,
    save_snapshot,
)
from tests import helpers as H
from tests.test_legal_actions_u7_1 import snap

HD, TL = CoinSide.HEADS, CoinSide.TAILS
SETS = (None, "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1")
CONTRACT = {"contract": "kyuura-client-api", "format": 1}


def uid(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def board(hand0, hand1, *, active0=H.CHARMANDER, active1=H.CHARMANDER, deck1=None, prizes1=None, discard1=()):
    """プレイヤー 0 の番。プレイヤー 0 の手札の先頭に錯乱ジム（まだ出していない）。"""
    me = {"active": {"card": active0, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": [H.CHAOS_GYM, *hand0], "deck": [H.FIRE] * 8, "prizes": [H.FIRE] * 2}
    them = {"active": {"card": active1, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": list(hand1), "deck": list(deck1 or [H.FIRE] * 8),
            "prizes": list(prizes1 or [H.FIRE] * 2), "discard": list(discard1)}
    state = H.build_test_state([me, them], turn_number=5)
    return apply_command(state, PlayTrainer(0, uid(state, 0, H.CHAOS_GYM)))


def tails(state, trainer):
    """プレイヤー 0 が手札の ``trainer`` を使い、錯乱ジムのコインが「うら」。"""
    return apply_command(H.with_coin_results(state, TL), PlayTrainer(0, uid(state, 0, trainer)))


def public(state):
    """使ったプレイヤー（0）と観戦者に見える値: 観測（決定の有無・種類・選ぶ数・選べるものの数を含む）と、見えるログ。"""
    return observe(state, 0), observe(state, None), visible_log(state, 0), visible_log(state, None)


def answer(state, choices):
    d = state.decision
    return apply_command(state, ResolveDecision(d.player, d.id, tuple(choices)))


TRADER_HAND = [H.POKEMON_TRADER, H.RATTATA]  # 使うプレイヤー（0）も、このカードを除く手札にポケモンのカードがいる


# 双子: プレイヤー 1（かわりに使うかもしれない人）の手札の中身だけが違う（枚数は同じ）。どちらでも 0 と観戦者に見える値は同じ
TWINS = {
    "trader": (H.POKEMON_TRADER, [H.CHARMANDER], [H.WATER]),  # このカードを除く手札にポケモンのカードがあるか
    "breeder": (H.POKEMON_BREEDER, [H.CHARIZARD], [H.WATER]),  # 場のたねポケモンに重ねられる 2 進化カードが手札にあるか（報告の双子）
    "good_manners": (H.GOOD_MANNERS, [H.WATER], [H.CHARMANDER]),  # 手札にたねポケモンがないか
}


class TwinTest(unittest.TestCase):
    def test_borrower_hand_does_not_change_public_values(self):
        for name, (trainer, usable, unusable) in TWINS.items():
            with self.subTest(trainer=name):
                mine = {H.POKEMON_BREEDER: [trainer, H.CHARIZARD], H.POKEMON_TRADER: TRADER_HAND}.get(trainer, [trainer])
                states = [tails(board(mine, hand), trainer) for hand in (usable, unusable)]
                self.assertEqual(public(states[0]), public(states[1]))
                for state in states:
                    self.assertEqual((state.decision.kind, state.decision.player, state.decision.options), (ACCEPT_REQUEST, 1, (1,)))

    def test_deck_and_prize_distribution(self):
        """エネルギー転送（山札から基本エネルギーを選ぶ）: かわりに使う人の基本エネルギーが山札にあるかサイドにあるかだけが違う双子（持ち主の知識の下限は配分によらない）。"""
        a = tails(board([H.ENERGY_SEARCH], [H.WATER], deck1=[H.RATTATA] * 7 + [H.WATER], prizes1=[H.RATTATA, H.RATTATA]), H.ENERGY_SEARCH)
        b = tails(board([H.ENERGY_SEARCH], [H.WATER], deck1=[H.RATTATA] * 8, prizes1=[H.RATTATA, H.WATER]), H.ENERGY_SEARCH)
        self.assertEqual(public(a), public(b))
        self.assertEqual(public(answer(a, ())), public(answer(b, ())))

    def test_psychic_control_choices_do_not_depend_on_the_users_hand(self):
        """ナツメのサイキックコントロール（同じ確かめで、相手のトラッシュから使えるカードを選ぶ）: 使う人（0）の手札の中身だけが違う双子で、相手（1）と観戦者に見える値が同じ。"""
        views, states = [], []
        for hand in ([H.CHARMANDER], [H.WATER]):
            me = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "bench": [H.RATTATA], "hand": [H.SABRINAS_PSYCHIC_CONTROL, *hand], "deck": [H.FIRE] * 8}
            them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "hand": [H.WATER], "deck": [H.FIRE] * 8, "discard": [H.POKEMON_TRADER]}
            state = H.build_test_state([me, them], turn_number=5)
            state = apply_command(H.with_coin_results(state, HD), PlayTrainer(0, uid(state, 0, H.SABRINAS_PSYCHIC_CONTROL)))
            views.append((observe(state, 1), observe(state, None), visible_log(state, 1), visible_log(state, None)))
            states.append(state)
        self.assertEqual(views[0], views[1])
        for state in states:
            self.assertEqual((state.decision.kind, state.decision.options), (USE_DISCARD_TRAINER, (uid(state, 1, H.POKEMON_TRADER, "discard"),)))


class AnswerTest(unittest.TestCase):
    def test_accept_when_usable(self):
        state = tails(board(TRADER_HAND, [H.CHARMANDER], deck1=[H.RATTATA] + [H.FIRE] * 7), H.POKEMON_TRADER)
        accepted = answer(state, (1,))
        self.assertEqual(accepted.trainer_in_use.using_player, 1)
        self.assertEqual(accepted.decision.player, 1)  # 使う人の決定（ポケモン交換おじさんの山札にもどすカード）
        kinds = [e["kind"] for e in accepted.log[len(state.log):]]
        self.assertEqual(kinds[0], "chaos_answered")

    def test_decline_discards_to_owner(self):
        for hand in ([H.CHARMANDER], [H.WATER]):
            state = tails(board(TRADER_HAND, hand), H.POKEMON_TRADER)
            card = state.trainer_in_use.card
            declined = answer(state, ())
            self.assertIn(card, declined.players[0].discard)
            self.assertEqual(declined.log[len(state.log)]["kind"], "chaos_answered")
            self.assertFalse(declined.log[len(state.log)]["accepted"])
            self.assertIsNone(declined.decision)

    def test_accept_when_not_usable_is_rejected_privately(self):
        """使うための条件を満たせない人が「使う」と答えると、状態・乱数・ログを変えずに拒否する（何度でも同じ。答える人にだけ返る）。そのあと「使わない」を受け付ける。"""
        state = tails(board(TRADER_HAND, [H.WATER]), H.POKEMON_TRADER)
        before = snap(state)
        codes = set()
        for _ in range(3):
            with self.assertRaises(IllegalActionError) as caught:
                answer(state, (1,))
            codes.add(caught.exception.code)
            self.assertEqual(snap(state), before)
        self.assertEqual(len(codes), 1)
        game = A.HostedGame(state.clone())
        result = game.submit(ResolveDecision(1, state.decision.id, (1,)), submitter=1)
        self.assertEqual(result.outcome, D.REJECTED)
        self.assertEqual(snap(game.state), before)
        self.assertIsNone(answer(state, ()).decision)

    def test_publicly_unusable_card_is_still_discarded_at_once(self):
        """ポケモンにつけて使うカード（プラスパワー）は、公開の情報だけで使えないと分かる: 今までどおり聞かずにトラッシュ（ログ chaos_not_borrowable。理由はカードの性質）。"""
        state = tails(board([H.PLUSPOWER], [H.WATER]), H.PLUSPOWER)
        self.assertIsNone(state.decision)
        events = [e for e in state.log if e["kind"] == "chaos_not_borrowable"]
        self.assertEqual(len(events), 1)
        self.assertNotIn("（", events[0]["reason"].split("カード")[0])

    def test_psychic_control_choice_not_usable_is_rejected(self):
        me = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "hand": [H.SABRINAS_PSYCHIC_CONTROL, H.WATER], "deck": [H.FIRE] * 8}
        them = {"active": {"card": H.CHARMANDER, "energy": [H.FIRE]}, "hand": [H.WATER], "deck": [H.FIRE] * 8, "discard": [H.POKEMON_TRADER]}
        state = H.build_test_state([me, them], turn_number=5)
        state = apply_command(H.with_coin_results(state, HD), PlayTrainer(0, uid(state, 0, H.SABRINAS_PSYCHIC_CONTROL)))
        before = snap(state)
        with self.assertRaises(IllegalActionError):
            answer(state, state.decision.options)
        self.assertEqual(snap(state), before)
        declined = answer(state, ())
        self.assertIsNone(declined.decision)


class StopsTest(unittest.TestCase):
    def test_existing_stops_are_kept(self):
        """使うことを選ぶと止める選択（CH1 など）・止める確かめは、今までどおり決定の続きの情報にある（答える人の候補にだけ出る）。"""
        state = tails(board([H.ENERGY_SEARCH], [H.WATER], deck1=[H.RATTATA] * 8, prizes1=[H.RATTATA] * 2), H.ENERGY_SEARCH)
        self.assertEqual(state.decision.context_value("unresolved_choices"), (1,))  # 山札に選べるカードがあると決まらない（v0.137）
        with self.assertRaises(UnsupportedError):
            answer(state, (1,))


class PersistenceTest(unittest.TestCase):
    def test_save_and_restore_while_waiting(self):
        for hand in ([H.CHARMANDER], [H.WATER]):
            state = tails(board(TRADER_HAND, hand), H.POKEMON_TRADER)
            report = restore_snapshot(loads_snapshot(dumps_snapshot(save_snapshot(state))))
            restored = report.state
            self.assertEqual(snap(restored), snap(state))
            self.assertEqual(snap(answer(restored, ())), snap(answer(state, ())))


class ClientApiTest(unittest.TestCase):
    def test_borrower_answers_through_client_api(self):
        state = tails(board(TRADER_HAND, [H.WATER]), H.POKEMON_TRADER)
        hub = ClientHub.from_state(state)
        borrower = hub.player(1)
        r = borrower.handle({**CONTRACT, "type": "candidates"})["response"]
        c = r["candidates"][0]
        self.assertEqual(c["kind"], L.KIND_ANSWER_DECISION)
        fields = {"game": r["game"], "revision": r["revision"], "candidate": c["id"]}
        stage = borrower.handle({**CONTRACT, "type": "inputs", **fields})["response"]["stages"][0]
        accept = [stage["options"][0]["id"]]
        sent = borrower.handle({**CONTRACT, "type": "submit", **fields, "choices": accept})
        self.assertEqual(sent["outcome"], D.REJECTED)  # 条件を満たせない（エンジンの拒否。答える人にだけ返る）
        self.assertEqual([hub.take_updates(a) for a in (0, "spectator")], [[], []])
        sent = borrower.handle({**CONTRACT, "type": "submit", **fields, "choices": []})
        self.assertEqual(sent["outcome"], D.ACCEPTED)
        self.assertEqual(hub.take_updates(0)[-1]["observation"], observe(answer(state, ()), 0))


# new_game からの合法な操作の列（事前に固定した seed。先攻の最初の番の手札に錯乱ジム・ポケモン交換おじさん・ポケモンのカードがあり、交換おじさんのコインが「うら」）
CHAOS_DECK = [c for c in (H.CHAOS_GYM, H.POKEMON_TRADER, H.CHARMANDER, H.CHARMELEON, H.VULPIX, H.PONYTA, H.GROWLITHE, H.MAGMAR) for _ in range(4)] + [H.FIRE] * 28
CHAOS_SEED = 16


class ConnectionTest(unittest.TestCase):
    """準備を U7 で終え（記録する対戦に同じコマンドを送る）、錯乱ジム → ポケモン交換おじさん（「うら」）→ 相手の不正な答え（拒否）→ 使わない → 番を終える。
    3 つの規約集合で、完全な再現用記録の構造・U4 の再実行・閲覧用記録の構造が通る。"""

    def test_from_new_game_record_and_replay(self):
        from kyuura_engine import replay_run, view_record
        from kyuura_engine.commands import EndTurn
        from kyuura_engine.replay_record import ReplayCollector
        from tests.test_legal_actions_u7_3 import CONNECT_DECK, Recording, setup_with_u7

        for conventions in SETS:
            with self.subTest(conventions=conventions):
                options = {} if conventions is None else {"conventions": conventions}
                start = A.start_game(CHAOS_DECK, CONNECT_DECK, CHAOS_SEED, **options)
                recording = Recording(start.state.clone())
                setup_with_u7(L.ActionHost(recording))
                collector, _ = ReplayCollector.start(CHAOS_DECK, CONNECT_DECK, CHAOS_SEED, include_git=False, **options)
                for command, submitter in recording.sent:
                    self.assertEqual(collector.submit(command, submitter=submitter).outcome, D.ACCEPTED, command)
                state = collector.state
                self.assertEqual((state.phase.name, state.current_player), ("MAIN", 0))
                self.assertEqual(collector.submit(PlayTrainer(0, uid(state, 0, H.CHAOS_GYM)), submitter=0).outcome, D.ACCEPTED)
                self.assertEqual(collector.submit(PlayTrainer(0, uid(collector.state, 0, H.POKEMON_TRADER)), submitter=0).outcome, D.ACCEPTED)
                d = collector.state.decision
                self.assertEqual((d.kind, d.player, d.options), (ACCEPT_REQUEST, 1, (1,)))
                self.assertFalse([e for e in collector.state.log if e["kind"] == "chaos_check"][-1]["heads"])
                self.assertEqual(collector.submit(ResolveDecision(1, d.id, (2,)), submitter=1).outcome, D.REJECTED)  # 選べるものにない（記録に残る拒否）
                self.assertEqual(collector.submit(ResolveDecision(1, d.id, ()), submitter=1).outcome, D.ACCEPTED)
                self.assertEqual(collector.submit(EndTurn(0), submitter=0).outcome, D.ACCEPTED)
                record = collector.close()  # 終局でなくても閉じられる（閉じた記録を U4 で最後まで照らす）
                report = replay_run.replay(record)
                self.assertEqual(report.status, replay_run.SUCCEEDED, report.mismatch)
                view_report, views = view_record.view_records_from_replay(record)
                self.assertEqual(view_report.status, replay_run.SUCCEEDED)
                for viewer, rec in views.items():
                    self.assertEqual(view_record.validate_view_record(rec).problems, (), viewer)
