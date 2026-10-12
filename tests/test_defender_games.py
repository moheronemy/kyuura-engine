"""ディフェンダーを入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで進める統合テスト（v0.2e）。

- ディフェンダーを使い、自分の場のポケモンを選んでつける（p.257）
- 相手の番まで残り、相手のワザで受けるダメージを 7 段階で -20 する（p.321）。ログの damage と、つけた記録で確かめる
- 次の相手の番の終わりにトラッシュする（使った番の終わりではない）。きぜつしたらいっしょにトラッシュ（p.323）。
  勝敗が決まった番は番の終わりが来ないので、ついたまま
- プラスパワー（5 段階）・ドードーの「みだれづき」（コイン）と組み合わせる
- すべての状態遷移で不変条件（カードの保存則・有効期限など）が保たれ、同じ seed・コマンドの列なら同じ結果
- でたらめなコマンドを混ぜても、拒否した操作は状態も乱数も変えない（決まった seed の軽い負荷テスト）

使う手順は tests/helpers.py の trainer_policy_command（ディフェンダーはワザを使う・番を終える直前に、手札にあるだけ
対戦ポケモンにつける）。kyuura の記録: NEO-2000-OFFICIAL-RULES、カード PMCG1-079。
"""

import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import DEFENDER, DEFENDER_DECK, DEFENDER_DECK_B, DODUO, coin_events, trainer_policy_command

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
SEEDS = range(8)


def full(state):
    return state_to_dict(state, format_version=4)


def play_game(seed, max_steps=6000):
    state = new_game(DEFENDER_DECK, DEFENDER_DECK_B, seed)
    commands = []
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands
        command = trainer_policy_command(state, janken_winner=seed % 2)
        commands.append(command)
        state = apply_command(state, command)
        problems = check_invariants(state)
        if problems:
            raise AssertionError(problems)
    raise AssertionError("決まった手数で終わらなかった")


def defender_history(state):
    """ディフェンダーごとに、つけた記録（attach_trainer）と、その後の行き先。"""
    log = [dict(e) for e in state.log]
    attached = {e["card"]: e for e in log if e["kind"] == "attach_trainer" and state.cards[e["card"]].card_id == DEFENDER}
    discarded = {e["card"]: e for e in log if e["kind"] == "discard_attached_trainer" and e["card"] in attached}
    knocked = {card: e for e in log if e["kind"] == "knock_out" for card in e.get("discarded_trainers", ()) if card in attached}
    return log, attached, discarded, knocked


class FullGameWithDefenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed) for seed in SEEDS}

    def test_games_end_with_valid_states(self):
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertIsNone(state.trainer_in_use)
                self.assertEqual(check_invariants(state), [])

    def test_every_defender_is_chosen_and_ends_at_the_right_time(self):
        """つけたディフェンダーは、次の相手の番の終わりにトラッシュするか、その前にきぜつでトラッシュするか、
        勝敗が決まって（番の終わりが来ずに）ついたまま。使った番の終わりにはトラッシュしない。"""
        used = 0
        for seed, (state, _) in self.games.items():
            log, attached, discarded, knocked = defender_history(state)
            on_field = {t.card: t for p in state.players for pk in p.in_play() for t in pk.trainers}
            for card, attach in attached.items():
                used += 1
                expiry = attach["discard_at_end_of_turn"]
                self.assertEqual(expiry, attach["turn"] + 1, (seed, card))  # 次の相手の番
                outcomes = [card in discarded, card in knocked, card in on_field]
                self.assertEqual(outcomes.count(True), 1, (seed, card, outcomes))
                if card in discarded:
                    self.assertEqual((discarded[card]["turn"], discarded[card]["reason"]), (expiry, "end_of_turn"))
                elif card in knocked:
                    self.assertLessEqual(knocked[card]["turn"], expiry)
                else:
                    self.assertGreaterEqual(expiry, state.turn_number)  # 対戦が終わったので番の終わりが来なかった
                owner = state.cards[card].owner
                self.assertEqual(state.players[owner].discard.count(card), 0 if card in on_field else 1)
        self.assertGreater(used, 0)

    def test_defender_reduces_the_damage_in_the_opponent_turn(self):
        """ディフェンダーの -20 は、そのカードをつけたポケモンが、次の相手の番に相手のワザで受けるダメージにだけ入る。"""
        reduced = Counter()
        for seed, (state, _) in self.games.items():
            log, attached, _, _ = defender_history(state)
            for event in log:
                if event["kind"] != "damage":
                    continue
                step7 = [m for m in event.get("modifiers", ()) if m[0] == 7]
                for step, card, amount in step7:
                    self.assertIn(card, attached)
                    self.assertEqual(amount, -20)
                    attach = attached[card]
                    self.assertEqual(event["pokemon"], attach["pokemon"])  # つけたポケモンが受けたダメージ
                    self.assertEqual(event["turn"], attach["turn"] + 1)  # 次の相手の番（相手のワザ）
                    self.assertEqual(event["player"], attach["player"])  # ダメージを受けたのはディフェンダーを使った側
                labels = [label for label, _ in event["steps"]]
                if step7:
                    reduced["damage_events"] += 1
                    self.assertEqual(labels.count("7 ディフェンダー"), len(step7))
                    last = event["steps"][-1][1]
                    self.assertEqual(event["amount"], max(0, last))
                    self.assertEqual(labels[-len(step7):], ["7 ディフェンダー"] * len(step7))  # 7 段階は 5 段階のあと
                    if any(m[0] == 5 for m in event["modifiers"]):
                        reduced["with_pluspower"] += 1
                    if event["amount"] == 0:
                        reduced["to_zero"] += 1
                    attacker = next(e for e in reversed(log[:log.index(event)]) if e["kind"] == "attack")
                    if state.cards[attacker["pokemon"]].card_id == DODUO:
                        reduced["coin_attack"] += 1
        self.assertTrue(all(reduced[k] > 0 for k in ("damage_events", "with_pluspower", "to_zero", "coin_attack")), reduced)

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed in list(SEEDS)[:3]:
            with self.subTest(seed=seed):
                state, commands = self.games[seed]
                again, again_commands = play_game(seed)
                self.assertEqual(again_commands, commands)
                self.assertEqual(full(again), full(state))
                replayed = new_game(DEFENDER_DECK, DEFENDER_DECK_B, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual([dict(e) for e in replayed.log], [dict(e) for e in state.log])

    def test_only_coins_use_randomness_after_setup(self):
        """ディフェンダー（使う・選ぶ・期限）は乱数を使わない。対戦準備のあとの乱数はコインだけ。"""
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(DEFENDER_DECK, DEFENDER_DECK_B, seed).rng)
                for _ in coin_events(state):
                    expected.getrandbits(1)
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))


class RandomCommandsWithDefenderTest(unittest.TestCase):
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
            # 相手の場のポケモンの番号・存在しない番号・古い決定の番号も混ぜる
            others = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0, -1, 999]
            return ResolveDecision(r.choice([d.player, 1 - d.player]), r.choice([d.id, d.id + 1, d.id - 1]),
                                   tuple(r.choice(list(d.options) + others) for _ in range(r.randint(0, 2))))
        if kind == 2:
            return Retreat(player, (), r.choice(uids))
        if kind == 3:
            return AttachEnergy(player, r.choice(uids), r.choice(uids))
        if kind == 4:
            return UseAttack(player, r.choice([0, 0, 1, -1]))
        return EndTurn(player)

    def test_random_commands(self):
        accepted = Counter()
        for seed in range(10):
            r = random.Random(seed)
            state = new_game(DEFENDER_DECK, DEFENDER_DECK_B, seed)
            for _ in range(300):
                if state.phase in TERMINAL:
                    break
                command = trainer_policy_command(state, janken_winner=seed % 2) if r.random() < 0.5 else self.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError:
                    accepted["rejected"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                if isinstance(command, ResolveDecision) and any(
                        e["kind"] == "attach_trainer" and new.cards[e["card"]].card_id == DEFENDER for e in new.log[len(state.log):]):
                    accepted["defender_attached"] += 1
                state = new
        self.assertGreater(accepted["defender_attached"], 0)
        self.assertGreater(accepted["rejected"], 0)


if __name__ == "__main__":
    unittest.main()
