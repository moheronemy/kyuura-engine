"""プラスパワーを入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで進める統合テスト（v0.2c）。

- プラスパワーをつけてワザを使い、ダメージ計算の 5 段階で +10 が加わる（p.321）
- 使った番の終わりにトラッシュする。勝敗が決まった番は、番の終わりが来ないのでついたまま（p.257・p.311）
- すべての状態遷移で不変条件（カードの保存則、ついているトレーナーの有効期限など）が保たれる
- 同じデッキ・seed・コマンドの列なら同じ結果。トレーナーは乱数を使わない
- でたらめなコマンドを混ぜても、拒否した操作は状態を変えない

使う手順は tests/helpers.py の trainer_policy_command（プラスパワーはワザを使う直前に、手札にあるだけつける）。
"""

import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command,
    check_invariants, expand_decklist, new_game, state_to_dict,
)
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BILL, DIGLETT, DRATINI, FIGHTING, FIRE, GROWLITHE, HITMONCHAN, MACHOP, PLUSPOWER, PONYTA, POTION, RATTATA, SEEL,
    STARYU, SWITCH, VOLTORB, WATER, find_seed, finish_setup, trainer_policy_command,
)

DECK_A = expand_decklist({
    GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 4, SWITCH: 4, PLUSPOWER: 4, FIRE: 24,
})
DECK_B = expand_decklist({
    STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, BILL: 2, POTION: 2, SWITCH: 2, PLUSPOWER: 4,
    WATER: 15, FIGHTING: 15,
})
TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)


def full(state):
    return state_to_dict(state, format_version=4)


def play_game(seed, *, janken_winner=0, max_steps=5000):
    state = new_game(DECK_A, DECK_B, seed)
    commands = []
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands
        command = trainer_policy_command(state, janken_winner=janken_winner)
        commands.append(command)
        state = apply_command(state, command)
        problems = check_invariants(state)
        if problems:
            raise AssertionError(problems)
    raise AssertionError("決まった手数で終わらなかった")


def pluspowers_played(state):
    return [e["card"] for e in state.log if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == PLUSPOWER]


class FullGameWithPlusPowerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, janken_winner=seed % 2) for seed in range(6)}

    def test_decks_are_legal_and_games_end(self):
        self.assertEqual((len(DECK_A), len(DECK_B)), (60, 60))
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertIsNone(state.trainer_in_use)
                self.assertEqual(check_invariants(state), [])

    def test_pluspower_is_used_and_applied_at_step_5(self):
        played = 0
        modified = 0
        for state, _ in self.games.values():
            played += len(pluspowers_played(state))
            for event in state.log:
                if event["kind"] == "damage" and "modifiers" in event:
                    modified += 1
                    labels = [label for label, _ in event["steps"]]
                    self.assertIn("5 プラスパワー", labels)
                    # 5 段階は弱点（3）・抵抗力（4）のあと
                    fifth = labels.index("5 プラスパワー")
                    self.assertTrue(all(not label.startswith(("3", "4")) for label in labels[fifth:]))
        self.assertGreater(played, 0)
        self.assertGreater(modified, 0)

    def test_every_pluspower_is_discarded_once_or_stays_only_at_the_end(self):
        """使ったプラスパワーは、その番の終わりにちょうど 1 回トラッシュする。勝敗が決まった番だけはついたまま。"""
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                discarded = Counter(e["card"] for e in state.log if e["kind"] == "discard_attached_trainer")
                self.assertTrue(all(count == 1 for count in discarded.values()))
                attached = {t.card for p in state.players for pk in p.in_play() for t in pk.trainers}
                for card in pluspowers_played(state):
                    self.assertTrue((card in discarded) != (card in attached), card)
                    owner = state.cards[card].owner
                    self.assertEqual(state.players[owner].discard.count(card), 1 if card in discarded else 0)
                for card in attached:  # 残っているのは、最後の番に使ったものだけ
                    t = next(t for p in state.players for pk in p.in_play() for t in pk.trainers if t.card == card)
                    self.assertEqual(t.discard_at_end_of_turn, state.turn_number)

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed, (state, commands) in list(self.games.items())[:3]:
            with self.subTest(seed=seed):
                again, again_commands = play_game(seed, janken_winner=seed % 2)
                self.assertEqual(again_commands, commands)
                self.assertEqual(full(again), full(state))
                replayed = new_game(DECK_A, DECK_B, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual([dict(e) for e in replayed.log], [dict(e) for e in state.log])

    def test_no_randomness_after_setup(self):
        for seed, (state, _) in self.games.items():
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(new_game(DECK_A, DECK_B, seed).rng))


class FirstTurnPlusPowerTest(unittest.TestCase):
    def test_first_player_uses_pluspower_and_attacks_on_the_first_turn(self):
        """正式な対戦開始から、先攻の最初の番にプラスパワーをつけてワザを使い、番の終わりにトラッシュする。"""
        def ready(state):
            p = state.players[0]
            ids = [state.cards[u].card_id for u in p.hand]
            return state.phase is Phase.SETUP_PLACEMENT and PLUSPOWER in ids and FIRE in ids and RATTATA in ids
        seed = find_seed(DECK_A, DECK_B, ready)
        state = new_game(DECK_A, DECK_B, seed)
        from kyuura_engine import PlaceStartingPokemon
        rattata = next(u for u in state.players[0].hand if state.cards[u].card_id == RATTATA)
        state = apply_command(state, PlaceStartingPokemon(0, rattata, ()))
        state = finish_setup(state, janken_winner=0)
        self.assertEqual((state.turn_number, state.current_player), (1, 0))
        p = state.players[0]
        fire = next(u for u in p.hand if state.cards[u].card_id == FIRE)
        pluspower = next(u for u in p.hand if state.cards[u].card_id == PLUSPOWER)
        state = apply_command(state, AttachEnergy(0, fire, p.active.card))
        state = apply_command(state, PlayTrainer(0, pluspower))
        state = apply_command(state, UseAttack(0, 0))  # コラッタ（無色）かみつく 20。相手のデッキに無色の弱点・抵抗力はない
        damage = [e for e in state.log if e["kind"] == "damage"][-1]
        self.assertEqual(damage["modifiers"], ((5, pluspower, 10),))
        self.assertEqual((damage["amount"], list(damage["steps"])), (30, [("1 基本となる計算", 20), ("5 プラスパワー", 30)]))
        if state.phase is Phase.TAKE_PRIZE:  # きぜつさせたら、サイド・交代のあとで番が終わる
            self.assertIn(pluspower, [t.card for t in state.players[0].active.trainers])
        else:
            self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))
            self.assertIn(pluspower, state.players[0].discard)


class RandomCommandsWithPlusPowerTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜる。拒否は状態を変えず、受け付けた状態は不変条件を満たす。"""

    def random_command(self, r, state):
        uids = list(state.cards) + [-1, 999]
        player = r.choice([0, 1, 0, 1, 2])
        d = state.decision
        kind = r.randrange(6)
        if kind == 0:
            hand = state.players[state.current_player].hand if state.current_player is not None else []
            return PlayTrainer(state.current_player if hand and r.random() < 0.7 else player, r.choice(hand or uids))
        if kind == 1 and d is not None:
            return ResolveDecision(r.choice([d.player, 1 - d.player]), r.choice([d.id, d.id + 1]),
                                   tuple(r.choice(list(d.options) + [0, -1]) for _ in range(r.randint(0, 2))))
        if kind == 2:
            return Retreat(player, (), r.choice(uids))
        if kind == 3:
            return AttachEnergy(player, r.choice(uids), r.choice(uids))
        if kind == 4:
            return UseAttack(player, r.choice([0, 1]))
        return EndTurn(player)

    def test_random_commands(self):
        accepted = Counter()
        for seed in range(8):
            r = random.Random(seed)
            state = new_game(DECK_A, DECK_B, seed)
            for _ in range(400):
                if state.phase in TERMINAL:
                    break
                command = trainer_policy_command(state, janken_winner=seed % 2) if r.random() < 0.5 else self.random_command(r, state)
                before = full(state)
                try:
                    new = apply_command(state, command)
                except EngineError:
                    self.assertEqual(full(state), before, command)
                    continue
                self.assertEqual(full(state), before, command)
                self.assertEqual(check_invariants(new), [])
                if isinstance(command, PlayTrainer):
                    accepted[state.cards[command.card].card_id] += 1
                state = new
        self.assertGreater(accepted[PLUSPOWER], 0)


if __name__ == "__main__":
    unittest.main()
