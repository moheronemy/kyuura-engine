"""v0.130: 対戦の中の所有者の変更の共通処理（docs/trade-please-ownership-v0.130.md 4 章・7 章）。

- ``zones.exchange_hand_cards``: 2 枚の移動・所有者の変更・出所・記録・ログを 1 回で行う（片方だけの状態を作らない）。不正な引数は状態を変えずに ``RuntimeError``
- 不変条件（``engine._ownership_problems``・デッキの保存則）が、所有者・出所・変更の記録・ログの食い違いを見つける
- 交換したあとの移動は新しい所有者を基準にする（トラッシュ・山札・サイド・場）。後から重ねたカードの所有者は変えない
- 書き出しの形式 33（出所・変更の記録）と、形式 1〜32 の拒否（黙って落とさない）。変更のない対戦の書き出しは v0.129 と同じ
- pickle・deepcopy・clone で同じ状態になる。v0.129 の状態の写し（項目のない pickle）は変更のない状態として読める
"""

from __future__ import annotations

import copy
import dataclasses
import pickle
import unittest

from kyuura_engine import check_invariants, state_to_dict
from kyuura_engine.engine import new_game
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import CardInstance, GameState, OwnershipChange, freeze_mapping
from kyuura_engine.zones import discard_from_hand, exchange_hand_cards, return_hand_cards_to_deck, shuffle_deck
from tests.helpers import FIRE, HITMONCHAN, POTION, RATTATA, build_test_state

TRAINER = 999  # 交換に使ったトレーナーの uid の代わり（この部品のテストでは、トレーナーの処理を通さない）


def board() -> GameState:
    return build_test_state([
        {"active": HITMONCHAN, "hand": [RATTATA, POTION, FIRE]},
        {"active": RATTATA, "hand": [HITMONCHAN, FIRE]},
    ])


def hand(state: GameState, player: int, card_id: str) -> int:
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)


def snapshot(state: GameState):
    return (pickle.dumps(state), len(state.log))


class ExchangeTest(unittest.TestCase):
    def test_exchange_moves_both_cards_and_changes_both_owners_at_once(self):
        state = board()
        given, taken = hand(state, 0, RATTATA), hand(state, 1, HITMONCHAN)
        others = {uid: card for uid, card in state.cards.items() if uid not in (given, taken)}
        number = exchange_hand_cards(state, 0, given, taken, trainer=TRAINER)
        self.assertEqual(number, 1)
        self.assertEqual(state.players[0].hand[-1], taken)
        self.assertEqual(state.players[1].hand[-1], given)
        self.assertNotIn(given, state.players[0].hand)
        self.assertNotIn(taken, state.players[1].hand)
        self.assertEqual((state.cards[given].owner, state.cards[given].origin, state.cards[given].deck_owner), (1, 0, 0))
        self.assertEqual((state.cards[taken].owner, state.cards[taken].origin, state.cards[taken].deck_owner), (0, 1, 1))
        # uid・カードの id は付け直さない。ほかのカードは同じもの（出所なし）
        self.assertEqual((state.cards[given].uid, state.cards[given].card_id), (given, RATTATA))
        self.assertEqual({uid: card for uid, card in state.cards.items() if uid not in (given, taken)}, others)
        self.assertTrue(all(card.origin is None for card in others.values()))
        self.assertEqual(state.ownership_changes, (
            OwnershipChange(given, RATTATA, 0, 1, 0, state.turn_number, TRAINER, 1),
            OwnershipChange(taken, HITMONCHAN, 1, 0, 1, state.turn_number, TRAINER, 1)))
        event = dict(state.log[-1])
        self.assertEqual(event["kind"], "cards_exchanged")
        self.assertEqual((event["player"], event["opponent"], event["given_card"], event["taken_card"], event["exchange"]), (0, 1, given, taken, 1))
        self.assertEqual(tuple(tuple(x) for x in event["ownership"]), ((given, 0, 1, 0), (taken, 1, 0, 1)))
        self.assertEqual(check_invariants(state), [])

    def test_invalid_arguments_change_nothing(self):
        state = board()
        given, taken = hand(state, 0, RATTATA), hand(state, 1, HITMONCHAN)
        deck = state.players[0].deck[0]
        before = snapshot(state)
        for args in ((given, given), (taken, given), (deck, taken), (given, state.players[1].deck[0]), (given, state.players[0].hand[1])):
            with self.subTest(args=args), self.assertRaises(RuntimeError):
                exchange_hand_cards(state, 0, *args, trainer=TRAINER)
            self.assertEqual(snapshot(state), before)
        # 所有者がゾーンと違う（壊れた状態）でも、変える前に止める
        broken = board()
        g, t = hand(broken, 0, RATTATA), hand(broken, 1, HITMONCHAN)
        broken.cards = freeze_mapping({**broken.cards, g: CardInstance(g, RATTATA, 1)})
        before = snapshot(broken)
        with self.assertRaises(RuntimeError):
            exchange_hand_cards(broken, 0, g, t, trainer=TRAINER)
        self.assertEqual(snapshot(broken), before)

    def test_re_exchange_keeps_the_origin_and_does_not_restore_silently(self):
        state = board()
        given, taken = hand(state, 0, RATTATA), hand(state, 1, HITMONCHAN)
        exchange_hand_cards(state, 0, given, taken, trainer=TRAINER)
        # 受け取ったカードを、もう一度交換する（プレイヤー 1 が使った側。プレイヤー 0 から受け取ったラッタを渡し、プレイヤー 0 の手札のエネルギーを受け取る）
        fire = hand(state, 0, FIRE)
        self.assertEqual(exchange_hand_cards(state, 1, given, fire, trainer=TRAINER + 1), 2)
        self.assertEqual((state.cards[given].owner, state.cards[given].origin), (0, 0))  # 出所と同じ所有者にもどったが、変更の記録は残る（origin は None にしない）
        self.assertEqual((state.cards[fire].owner, state.cards[fire].origin), (1, 0))
        self.assertEqual([(c.card, c.previous, c.owner, c.origin, c.exchange) for c in state.ownership_changes],
                         [(given, 0, 1, 0, 1), (taken, 1, 0, 1, 1), (given, 1, 0, 0, 2), (fire, 0, 1, 0, 2)])
        self.assertEqual(check_invariants(state), [])

    def test_new_game_conservation_counts_by_the_origin(self):
        deck = [RATTATA] * 4 + [FIRE] * 56
        state = new_game(deck, [HITMONCHAN] * 4 + [FIRE] * 56, seed=3)
        given = state.players[0].hand[0]
        taken = state.players[1].hand[0]
        exchange_hand_cards(state, 0, given, taken, trainer=TRAINER)
        self.assertEqual(check_invariants(state), [])
        # 出所を落とすと、デッキの保存則と変更の記録の両方が食い違いを見つける
        tampered = copy.deepcopy(state)
        tampered.cards = freeze_mapping({**tampered.cards, given: CardInstance(given, state.cards[given].card_id, 1)})
        problems = check_invariants(tampered)
        self.assertTrue(any("対戦開始時のデッキと違う" in p for p in problems), problems)
        self.assertTrue(any("最後の値" in p for p in problems), problems)


class InvariantTamperingTest(unittest.TestCase):
    def setUp(self):
        self.state = board()
        self.given, self.taken = hand(self.state, 0, RATTATA), hand(self.state, 1, HITMONCHAN)
        exchange_hand_cards(self.state, 0, self.given, self.taken, trainer=TRAINER)

    def assert_found(self, state, text):
        problems = check_invariants(state)
        self.assertTrue(any(text in p for p in problems), problems)

    def test_owner_not_matching_the_zone(self):
        state = copy.deepcopy(self.state)
        state.cards = freeze_mapping({**state.cards, self.given: dataclasses.replace(state.cards[self.given], owner=0)})
        self.assert_found(state, "持ち主でない")

    def test_one_sided_change_is_found(self):
        state = copy.deepcopy(self.state)
        state.ownership_changes = state.ownership_changes[:1]
        self.assert_found(state, "2 つずつではない")

    def test_card_with_origin_but_no_change(self):
        state = copy.deepcopy(self.state)
        other = hand(state, 0, POTION)
        state.cards = freeze_mapping({**state.cards, other: dataclasses.replace(state.cards[other], origin=0)})
        self.assert_found(state, "変更のないカード")

    def test_wrong_origin_in_the_record(self):
        state = copy.deepcopy(self.state)
        first, second = state.ownership_changes
        state.ownership_changes = (dataclasses.replace(first, origin=1), second)
        self.assert_found(state, "前の所有者・出所")

    def test_log_must_match_the_record(self):
        state = copy.deepcopy(self.state)
        state.log = state.log[:-1]
        self.assert_found(state, "交換のログ")


class MovementAfterExchangeTest(unittest.TestCase):
    """交換したあとの移動は、新しい所有者（受け取ったプレイヤー）のゾーンに置く。出所のプレイヤーのゾーンに置く処理はない。"""

    def setUp(self):
        self.state = board()
        self.given, self.taken = hand(self.state, 0, POTION), hand(self.state, 1, HITMONCHAN)
        exchange_hand_cards(self.state, 0, self.given, self.taken, trainer=TRAINER)

    def test_discard_goes_to_the_new_owner(self):
        state = self.state
        discard_from_hand(state, 1, (self.given,))  # プレイヤー 0 のデッキのきずぐすりを、受け取ったプレイヤー 1 がトラッシュする
        self.assertIn(self.given, state.players[1].discard)
        self.assertNotIn(self.given, state.players[0].discard)
        self.assertEqual(check_invariants(state), [])
        # もとの持ち主（出所）の手札からはトラッシュできない（確認の漏れとして止める）
        state2 = board()
        g, t = hand(state2, 0, POTION), hand(state2, 1, HITMONCHAN)
        exchange_hand_cards(state2, 0, g, t, trainer=TRAINER)
        with self.assertRaises(Exception):
            discard_from_hand(state2, 0, (g,))

    def test_return_to_deck_and_shuffle_use_the_new_owner(self):
        state = self.state
        return_hand_cards_to_deck(state, 0, (self.taken,), trainer=TRAINER + 1)
        shuffle_deck(state, 0)
        self.assertIn(self.taken, state.players[0].deck)
        self.assertNotIn(self.taken, state.players[1].deck)
        self.assertEqual(check_invariants(state), [])


class SerializationTest(unittest.TestCase):
    def test_format_33_writes_origin_and_changes(self):
        self.assertEqual(FORMAT_VERSIONS[-1], 33)
        state = board()
        given, taken = hand(state, 0, RATTATA), hand(state, 1, HITMONCHAN)
        exchange_hand_cards(state, 0, given, taken, trainer=TRAINER)
        data = state_to_dict(state, 33)
        self.assertEqual(data["cards"][str(given)], {"card_id": RATTATA, "owner": 1, "origin": 0})
        self.assertEqual(data["cards"][str(taken)], {"card_id": HITMONCHAN, "owner": 0, "origin": 1})
        self.assertTrue(all("origin" not in record for uid, record in data["cards"].items() if int(uid) not in (given, taken)))
        self.assertEqual(data["ownership_changes"], [
            {"card": given, "card_id": RATTATA, "previous": 0, "owner": 1, "origin": 0, "turn": state.turn_number, "trainer_card": TRAINER, "exchange": 1},
            {"card": taken, "card_id": HITMONCHAN, "previous": 1, "owner": 0, "origin": 1, "turn": state.turn_number, "trainer_card": TRAINER, "exchange": 1}])
        before = snapshot(state)
        for version in FORMAT_VERSIONS[:-1]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, version)
        self.assertEqual(snapshot(state), before)

    def test_no_change_keeps_the_old_formats(self):
        state = board()
        for version in FORMAT_VERSIONS[:-1]:
            data = state_to_dict(state, version)
            self.assertNotIn("ownership_changes", data)
            self.assertTrue(all(set(record) == {"card_id", "owner"} for record in data["cards"].values()))
        latest = state_to_dict(state, 33)
        self.assertEqual(latest["ownership_changes"], [])
        self.assertEqual(latest["user_ownership_rules"], [])  # とりかえっこプリーズのない対戦（登録表とカードの組から求める識別の情報）
        self.assertEqual({key: value for key, value in latest.items() if key not in ("ownership_changes", "user_ownership_rules", "format_version")}, {key: value for key, value in state_to_dict(state, 32).items() if key != "format_version"})

    def test_pickle_deepcopy_clone_keep_the_owners(self):
        state = board()
        given, taken = hand(state, 0, RATTATA), hand(state, 1, HITMONCHAN)
        exchange_hand_cards(state, 0, given, taken, trainer=TRAINER)
        for copied in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
            self.assertEqual(state_to_dict(copied, 33), state_to_dict(state, 33))
            self.assertEqual(copied.ownership_changes, state.ownership_changes)
            self.assertEqual(check_invariants(copied), [])
        # 複製のあとで交換しても、もとの状態は変わらない（カードの表は置きかえる。共有の表を書きかえない）
        clone = state.clone()
        exchange_hand_cards(clone, 0, hand(clone, 0, POTION), hand(clone, 1, FIRE), trainer=TRAINER + 1)
        self.assertEqual(len(state.ownership_changes), 2)
        self.assertEqual(state.cards[hand(state, 0, POTION)].owner, 0)

    def test_state_without_the_new_field_reads_as_no_change(self):
        state = board()
        data = state.__getstate__()
        data.pop("ownership_changes", None)
        old = object.__new__(GameState)
        old.__setstate__(data)
        self.assertEqual(old.ownership_changes, ())
        self.assertEqual(check_invariants(old), [])
        self.assertEqual(state_to_dict(old, 32), state_to_dict(state, 32))


if __name__ == "__main__":
    unittest.main()
