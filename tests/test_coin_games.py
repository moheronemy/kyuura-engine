"""コインを投げるワザ（ドードーの「みだれづき」）を入れた 60 枚のデッキで、正式な対戦開始（new_game）から
勝敗まで進める統合テスト（v0.2d）。

- ワザを使うたびにコインを 2 枚投げ、ダメージ計算の 1 段階が「おもて」の数×10 になる（p.231・p.320・p.321）
- 対戦準備（山札を切る）のあとで乱数を使うのはコインだけ。コイン 1 枚につき乱数 1 回
- 同じデッキ・seed・コマンドの列なら同じ結果（コインも同じ）
- コインの前に複製した状態から続けても、コインのあとに乱数を JSON で保存・復元して続けても同じ結果
- でたらめなコマンドを混ぜても、拒否した操作は状態も乱数も変えない（決まった seed の軽い負荷テスト）

使う手順は tests/helpers.py の trainer_policy_command（プラスパワーはワザを使う直前に、手札にあるだけつける）。
kyuura の記録: NEO-2000-OFFICIAL-RULES、カード PMCG1-061。
"""

import copy
import json
import pickle
import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint, rng_from_json, rng_state_to_json

from tests.helpers import (
    CARD_DATA_COMMIT_SINCE_V0_69,
    with_card_data_commit_before_v0_69,
    DODUO, DODUO_DECK, DODUO_TRAINER_DECK, PLUSPOWER, WATER_FIGHTING_DECK, coin_events, trainer_policy_command,
)

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
SEEDS = range(8)


def full(state):
    return state_to_dict(state, format_version=4)


def decks(seed):
    """seed ごとに組み合わせを変える（プラスパワーのあるデッキ・ないデッキ、相手もドードーを使う）。"""
    return [(DODUO_TRAINER_DECK, WATER_FIGHTING_DECK), (DODUO_DECK, DODUO_TRAINER_DECK)][seed % 2]


def play_game(seed, max_steps=5000):
    deck0, deck1 = decks(seed)
    state = new_game(deck0, deck1, seed)
    commands, states = [], [state]
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, states
        command = trainer_policy_command(state, janken_winner=seed % 2)
        commands.append(command)
        state = apply_command(state, command)
        problems = check_invariants(state)
        if problems:
            raise AssertionError(problems)
        states.append(state)
    raise AssertionError("決まった手数で終わらなかった")


def doduo_attacks(state):
    """ドードーのワザごとに、(attack の位置, コインの記録, damage の記録)。"""
    log = [dict(e) for e in state.log]
    result = []
    for i, event in enumerate(log):
        if event["kind"] == "attack" and state.cards[event["pokemon"]].card_id == DODUO:
            flips = [e for e in log[i + 1:i + 3] if e["kind"] == "coin_flip"]
            damage = log[i + 3]
            result.append((i, flips, damage))
    return result


class FullGameWithCoinsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed) for seed in SEEDS}

    def test_games_end_with_valid_states(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertEqual(check_invariants(state), [])
                self.assertEqual((len(state.decklists[0]), len(state.decklists[1])), (60, 60))

    def test_every_fury_attack_flips_two_coins_and_uses_the_heads(self):
        counted = Counter()
        for seed, (state, _, _) in self.games.items():
            for index, flips, damage in doduo_attacks(state):
                attack = state.log[index]
                self.assertEqual(len(flips), 2, (seed, index))
                self.assertEqual([f["number"] for f in flips], [1, 2])
                self.assertTrue(all(f["player"] == attack["player"] and f["card"] == attack["pokemon"]
                                    and f["effect"] == f"{DODUO}#0" and f["source"] == "attack" for f in flips))
                self.assertEqual(damage["kind"], "damage")
                heads = sum(f["result"] == "heads" for f in flips)
                self.assertEqual(damage["steps"][0], ("1 基本となる計算", 10 * heads))
                if heads == 0:
                    self.assertEqual((damage["amount"], damage.get("stopped_after_step_2")), (0, True))
                    self.assertNotIn("modifiers", damage)
                counted[heads] += 1
                if "modifiers" in damage:
                    counted["pluspower"] += 1
        # 0・1・2 枚のどれも、プラスパワーとの組み合わせも、実際の対戦で起きている
        self.assertTrue(all(counted[k] > 0 for k in (0, 1, 2, "pluspower")), counted)

    def test_coins_are_the_only_randomness_after_setup(self):
        """対戦準備のあとの乱数は、コイン 1 枚につき getrandbits(1) 1 回だけ（ほかの処理は乱数を使わない）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                deck0, deck1 = decks(seed)
                expected = copy_rng(new_game(deck0, deck1, seed).rng)
                bits = [expected.getrandbits(1) for _ in coin_events(state)]
                self.assertEqual([e["result"] for e in coin_events(state)], ["heads" if b else "tails" for b in bits])
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed in list(SEEDS)[:3]:
            with self.subTest(seed=seed):
                state, commands, _ = self.games[seed]
                again, again_commands, _ = play_game(seed)
                self.assertEqual(again_commands, commands)
                self.assertEqual(full(again), full(state))
                deck0, deck1 = decks(seed)
                replayed = new_game(deck0, deck1, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual([dict(e) for e in replayed.log], [dict(e) for e in state.log])
                self.assertEqual(rng_fingerprint(replayed.rng), rng_fingerprint(state.rng))

    def test_resume_from_a_copy_made_before_the_coins(self):
        """ドードーがワザを使う直前の状態を複製（clone・deepcopy・pickle）して続けても、同じコイン・同じ結果。"""
        checked = 0
        for seed, (state, commands, states) in list(self.games.items())[:4]:
            for i, command in enumerate(commands):
                before = states[i]
                if not (isinstance(command, UseAttack) and before.card_def(before.players[command.player].active.card).id == DODUO):
                    continue
                for copied in (before.clone(), copy.deepcopy(before), pickle.loads(pickle.dumps(before))):
                    resumed = copied
                    for later in commands[i:]:
                        resumed = apply_command(resumed, later)
                    self.assertEqual(full(resumed), full(state))
                checked += 1
                break
        self.assertGreater(checked, 0)

    def test_save_the_rng_after_the_coins_and_continue(self):
        """ドードーがワザを使った直後に乱数を JSON で保存し、もどした乱数で続けても同じ結果（乱数の保存・復元）。

        ゲーム状態全体を JSON から読み込む機能は未実装なので、乱数以外は複製した状態を使う。
        """
        checked = 0
        for seed, (state, commands, states) in list(self.games.items())[:4]:
            for i, command in enumerate(commands):
                if not (isinstance(command, UseAttack) and states[i].card_def(states[i].players[command.player].active.card).id == DODUO):
                    continue
                after = states[i + 1]
                saved = json.dumps(rng_state_to_json(after.rng))
                resumed = after.clone()
                resumed.rng = rng_from_json(json.loads(saved))
                for later in commands[i + 1:]:
                    resumed = apply_command(resumed, later)
                self.assertEqual(full(resumed), full(state))
                checked += 1
        self.assertGreater(checked, 0)

    def test_pluspower_is_discarded_or_left_only_at_the_end(self):
        for seed, (state, _, _) in self.games.items():
            played = [e["card"] for e in state.log if e["kind"] == "play_trainer" and state.cards[e["card"]].card_id == PLUSPOWER]
            discarded = {e["card"] for e in state.log if e["kind"] == "discard_attached_trainer"}
            attached = {t.card for p in state.players for pk in p.in_play() for t in pk.trainers}
            for card in played:
                self.assertTrue((card in discarded) != (card in attached), (seed, card))


class GoldenCoinGameTest(unittest.TestCase):
    """コインを投げる対戦の結果を固定値と比べる（Python 3.11・3.12・3.13 で同じ値になることを確かめた。v0.2d）。

    ここが失敗したら、同じデッキ・seed・手順で以前と違う対戦（違うコイン）になっている。乱数の使い方・カードの
    番号の付け方・状態の形を意図して変えたのでない限り、エンジンの不具合。
    """

    def test_fixed_seed_game(self):
        import hashlib

        state, commands, _ = play_game(1)
        self.assertEqual((len(commands), state.turn_number, state.result.winner), (115, 39, 1))
        coins = "".join("H" if e["result"] == "heads" else "T" for e in coin_events(state))
        self.assertEqual(coins, "HHHHHTTHHHHHHHHHTHHHTTHTTH")
        # 効果の登録表の id（版の名前）は、登録を加えるたびに変わるので、ハッシュに入れずに別に確かめる（v0.2e）。
        # ハッシュの値は、v0.2d のコミット e66390a のエンジンで同じ対戦から計算した値と同じ（対戦の中身は変わっていない）
        data = full(state)
        # v0.69: 写しの元を上げた（7d3f4ca）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT_SINCE_V0_69)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        text = json.dumps(data, sort_keys=True, ensure_ascii=False)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), "d0cd41e260f89d547898fcff3e605f0d5c946a1af487cc481d910d007135cc90")


class RandomCommandsWithCoinsTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜる（決まった seed）。拒否は状態も乱数も変えず、受け付けた状態は不変条件を満たす。"""

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
            return UseAttack(player, r.choice([0, 0, 1, -1]))
        return EndTurn(player)

    def test_random_commands(self):
        accepted_attacks = 0
        rejected = 0
        for seed in range(10):
            r = random.Random(seed)
            deck0, deck1 = decks(seed)
            state = new_game(deck0, deck1, seed)
            for _ in range(300):
                if state.phase in TERMINAL:
                    break
                command = trainer_policy_command(state, janken_winner=seed % 2) if r.random() < 0.5 else self.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError:
                    rejected += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                flipped = len(coin_events(new, len(state.log)))
                if flipped:
                    self.assertIsInstance(command, UseAttack)
                    self.assertEqual(flipped, 2)
                    accepted_attacks += 1
                state = new
        self.assertGreater(accepted_attacks, 0)
        self.assertGreater(rejected, 0)


if __name__ == "__main__":
    unittest.main()
