"""トレーナーを入れた 60 枚のデッキで、正式な対戦開始（new_game）から対戦を進める統合テスト（v0.2b）。

- 各トレーナー（マサキ・きずぐすり・ポケモンいれかえ）を使い、効果を解決して、番の進行を続けられる
- 勝敗が決まるまで進む。すべての状態遷移で不変条件（カードの保存則など）が保たれる（apply_command が検査する）
- 同じデッキ・seed・コマンドの列なら同じ結果（再現性）
- でたらめなコマンドを混ぜても、拒否した操作は状態を変えない

使う手順は tests/helpers.py の trainer_policy_command（対戦相手の AI ではない決まった手順）。
"""

import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, DrawMulliganCards, EndTurn, EngineError, EvolvePokemon, Phase, PlaceStartingPokemon, PlayBasicToBench,
    PlayTrainer, PromoteActive, ReportJankenResult, ResolveDecision, Retreat, TakePrize, UseAttack, UsePokemonPower,
    apply_command, check_invariants, expand_decklist, new_game, state_to_dict,
)
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BILL, DIGLETT, DRATINI, FIGHTING, FIRE, GROWLITHE, HITMONCHAN, MACHOP, PONYTA, POTION, RATTATA, SEEL, STARYU,
    SWITCH, VOLTORB, WATER, find_seed, finish_setup, trainer_policy_command,
)

FIRE_TRAINER_DECK = expand_decklist({
    GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 4, SWITCH: 4, FIRE: 28,
})
WATER_TRAINER_DECK = expand_decklist({
    STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, BILL: 4, POTION: 4, SWITCH: 4, WATER: 14, FIGHTING: 14,
})
TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)


def full(state):
    return state_to_dict(state, format_version=3)


def play_game(seed, *, janken_winner=0, max_steps=5000):
    """終わるまで決まった手順で進める。送ったコマンドと最後の状態を返す。"""
    state = new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed)
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


def trainers_played(state):
    return Counter(state.cards[e["card"]].card_id for e in state.log if e["kind"] == "play_trainer")


class TrainerDeckTest(unittest.TestCase):
    def test_decks_are_legal(self):
        for deck in (FIRE_TRAINER_DECK, WATER_TRAINER_DECK):
            self.assertEqual(len(deck), 60)
        state = new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, 0)
        self.assertEqual(len(state.cards), 120)


class FullGameWithTrainersTest(unittest.TestCase):
    """正式な対戦開始から勝敗が決まるまで、トレーナーを使いながら進める。"""

    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, janken_winner=seed % 2) for seed in range(6)}

    def test_games_reach_the_end(self):
        for seed, (state, commands) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertIsNotNone(state.result)
                self.assertIsNone(state.trainer_in_use)
                self.assertIsNone(state.decision)
                self.assertEqual(check_invariants(state), [])

    def test_every_trainer_is_used_and_resolved(self):
        total = Counter()
        for state, _ in self.games.values():
            total += trainers_played(state)
            kinds = [e["kind"] for e in state.log]
            # 使ったトレーナーは、すべて説明にしたがい終わってトラッシュされた
            self.assertEqual(kinds.count("play_trainer"), kinds.count("discard_trainer"))
        self.assertGreater(total[BILL], 0)
        self.assertGreater(total[POTION], 0)
        self.assertGreater(total[SWITCH], 0)

    def test_effects_appear_in_the_log_in_order(self):
        """使う → 効果 → トラッシュの順（p.310）。きずぐすり・ポケモンいれかえは決定のあとに効果。"""
        expected_effect = {BILL: "draw", POTION: "remove_damage_counters", SWITCH: "switch"}
        for state, _ in self.games.values():
            log = state.log
            for i, event in enumerate(log):
                if event["kind"] != "play_trainer":
                    continue
                card_id = state.cards[event["card"]].card_id
                self.assertEqual(log[i + 1]["kind"], expected_effect[card_id])
                self.assertEqual((log[i + 2]["kind"], log[i + 2]["card"]), ("discard_trainer", event["card"]))

    def test_trainer_cards_end_in_the_discard_or_elsewhere_but_never_in_use(self):
        for state, _ in self.games.values():
            for event in state.log:
                if event["kind"] == "discard_trainer":
                    owner = event["player"]
                    self.assertIn(event["card"], state.players[owner].discard)

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed, (state, commands) in list(self.games.items())[:3]:
            with self.subTest(seed=seed):
                again, again_commands = play_game(seed, janken_winner=seed % 2)
                self.assertEqual(again_commands, commands)
                self.assertEqual(full(again), full(state))
                replayed = new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual(full(replayed), full(state))
                self.assertEqual([dict(e) for e in replayed.log], [dict(e) for e in state.log])

    def test_trainers_do_not_use_randomness(self):
        """山札を切るのは対戦準備だけ。マサキは山札の上から引くだけで、乱数を使わない（p.312）。"""
        for seed, (state, _) in self.games.items():
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed).rng))


class FirstTurnTrainerTest(unittest.TestCase):
    def test_first_player_can_use_a_trainer_on_the_first_turn(self):
        """先攻の最初の番にトレーナーを使う制限はない（p.309・p.310 に規定がない。kyuura first_turn_actions）。"""
        seed = find_seed(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, lambda s: s.phase is Phase.SETUP_PLACEMENT and any(
            s.cards[u].card_id == BILL for u in s.players[0].hand))
        state = finish_setup(new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed), janken_winner=0)
        self.assertEqual((state.phase, state.turn_number, state.current_player), (Phase.MAIN, 1, 0))
        bill = next(u for u in state.players[0].hand if state.cards[u].card_id == BILL)
        hand, deck = len(state.players[0].hand), len(state.players[0].deck)
        state = apply_command(state, PlayTrainer(0, bill))
        self.assertEqual((len(state.players[0].hand), len(state.players[0].deck)), (hand - 1 + 2, deck - 2))
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))


class TrainerDecisionInRealGameTest(unittest.TestCase):
    """正式な対戦の中で、トレーナーの決定を待っている間は、決定に答えるコマンドしか受け付けない。"""

    def test_only_resolve_decision_is_accepted(self):
        for seed in range(30):
            state = new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed)
            while state.phase not in TERMINAL and not (state.phase is Phase.DECISION and state.trainer_in_use):
                state = apply_command(state, trainer_policy_command(state))
            if state.phase is Phase.DECISION:
                break
        else:
            self.fail("トレーナーの決定を待つ局面が見つからない")
        p = state.players[state.current_player]
        card = p.hand[0] if p.hand else 0
        pokemon = p.active.card
        before = full(state)
        for command in (
            PlaceStartingPokemon(0, card), DrawMulliganCards(0, 0), ReportJankenResult(0), PlayBasicToBench(0, card),
            AttachEnergy(0, card, pokemon), Retreat(0, (), pokemon), UseAttack(0, 0), EndTurn(0), TakePrize(0, 0),
            PromoteActive(0, pokemon), PlayTrainer(state.current_player, card),
            EvolvePokemon(0, card, p.active.pokemon_id),  # v0.4a から処理する（決定を待つ間は進化できない）
        ):
            with self.subTest(command=type(command).__name__):
                with self.assertRaises(EngineError) as ctx:
                    apply_command(state, command)
                self.assertEqual(ctx.exception.code, "WRONG_PHASE")
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, UsePokemonPower(0, pokemon))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_ACTION")
        self.assertEqual(full(state), before)
        done = apply_command(state, trainer_policy_command(state))
        self.assertEqual(done.phase, Phase.MAIN)
        self.assertIsNone(done.trainer_in_use)


class RandomCommandsWithTrainersTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜて送る。拒否は状態を変えず、受け付けた状態は不変条件を満たす。"""

    def random_command(self, r, state):
        uids = list(state.cards) + [-1, 999]
        player = r.choice([0, 1, 0, 1, 2])
        d = state.decision
        kind = r.randrange(6)
        if kind == 0:
            return PlayTrainer(player, r.choice(uids))
        if kind == 1 and d is not None:
            options = list(d.options) + [0, -1, 999]
            return ResolveDecision(r.choice([d.player, 1 - d.player]), r.choice([d.id, d.id + 1, d.id - 1]),
                                   tuple(r.choice(options) for _ in range(r.randint(0, 2))))
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
            state = new_game(FIRE_TRAINER_DECK, WATER_TRAINER_DECK, seed)
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
                self.assertEqual(full(state), before, command)  # 受け付けても、渡した状態は変わらない
                self.assertEqual(check_invariants(new), [])
                accepted[type(command).__name__] += 1
                state = new
        self.assertGreater(accepted["PlayTrainer"], 0)
        self.assertGreater(accepted["ResolveDecision"], 0)


if __name__ == "__main__":
    unittest.main()
