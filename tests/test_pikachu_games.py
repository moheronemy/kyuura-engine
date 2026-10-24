"""ピカチュウ（自分へのダメージ）を入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで進める統合テスト（v0.2f）。

- 「でんげき」: 相手にダメージ → コイン 1 枚 → 「うら」なら自分にも 10（p.125・p.320）。プラスパワー（5 段階）と
  ディフェンダー（7 段階）は自分へのダメージにも効く（p.257・p.321）
- 自分のワザで自分のポケモンがきぜつする。同じワザで両方の対戦ポケモンがきぜつする（同時。p.324）
- サイドは、きぜつしたポケモンの相手側のプレイヤーが取る。すべて取ってから p.311 の表で判定し、両方が同時に
  取り終えたらサドン・デス（延長戦は未実装なので止める）。バトル場には番でないプレイヤーが先に出す（pp.323〜324）
- すべての状態遷移で不変条件が保たれ、同じ seed・コマンドの列なら同じ結果。乱数を使うのはコインだけ
- でたらめなコマンドを混ぜても、拒否した操作は状態も乱数も変えない（決まった seed の軽い負荷テスト）

使う seed（``SEEDS``）の対戦には、自分のきぜつ・同時のきぜつ・サドン・デス（seed 9）・プラスパワーやディフェンダーをつけた
ピカチュウの自分へのダメージが起こる（v0.2f のエンジンで確かめた。起こらなくなったらテストが失敗する）。
使う手順は tests/helpers.py の trainer_policy_command。kyuura の記録: NEO-2000-OFFICIAL-RULES、カード PMCG1-035。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine import judge
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    CARD_DATA_COMMIT,
    with_card_data_commit_before_v0_69,
    DEFENDER, PIKACHU_DECK, PIKACHU_DECK_B, PLUSPOWER, coin_events, trainer_policy_command,
)

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
# 自然な対戦の中で次が起こる seed を選んだ（v0.2f のエンジンで seed 0〜39 を調べた）: 同時のきぜつ・自分のきぜつ
# （0・9・18・24・31）、サドン・デス（9）、プラスパワーつきの自分へのダメージ（36）、ディフェンダーつき（11・34）
SEEDS = (0, 9, 11, 18, 24, 31, 34, 36)


def full(state):
    return state_to_dict(state, format_version=4)


def play_game(seed, max_steps=6000):
    state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, seed)
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


def attacks(state):
    """ワザごとに、(attack の記録, そのワザの処理で出た記録の並び)。次の attack・turn_start の前まで。"""
    log = [dict(e) for e in state.log]
    result = []
    for i, event in enumerate(log):
        if event["kind"] != "attack":
            continue
        j = i + 1
        while j < len(log) and log[j]["kind"] not in ("attack", "turn_start"):
            j += 1
        result.append((event, log[i + 1:j]))
    return result


class FullGameWithPikachuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed) for seed in SEEDS}

    def test_games_end_with_valid_states(self):
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH))
                self.assertEqual(check_invariants(state), [])
                self.assertIsNone(state.decision)

    def test_thunder_jolt_elements(self):
        """でんげき: 相手へのダメージ → コイン 1 枚 → 「うら」のときだけ自分へのダメージ。自分へのダメージの変更効果は、
        ピカチュウについているプラスパワー（5 段階 +10）とディフェンダー（7 段階 -20）だけ。"""
        counted = Counter()
        for seed, (state, _) in self.games.items():
            log = [dict(e) for e in state.log]
            attached_to = {e["card"]: e["pokemon"] for e in log if e["kind"] == "attach_trainer"}
            for attack, events in attacks(state):
                if attack["attack"] != "でんげき":
                    continue
                kinds = [e["kind"] for e in events]
                self.assertEqual(kinds[:2], ["damage", "coin_flip"], (seed, attack))
                coin = events[1]
                self.assertEqual((coin["player"], coin["card"], coin["effect"]), (attack["player"], attack["pokemon"], "PMCG1-035#1"))
                own = [e for e in events if e["kind"] == "damage" and e.get("target") == "self"]
                if coin["result"] == "heads":
                    self.assertEqual(own, [])
                    counted["heads"] += 1
                    continue
                self.assertEqual(len(own), 1)
                own = own[0]
                self.assertEqual(kinds[2], "damage")
                self.assertEqual((own["player"], own["pokemon"]), (attack["player"], attack["pokemon"]))
                total = 10
                for step, card, amount in own.get("modifiers", ()):
                    self.assertEqual(attached_to[card], attack["pokemon"])  # ピカチュウ自身についているカード
                    self.assertEqual((step, state.cards[card].card_id, amount),
                                     (5, PLUSPOWER, 10) if step == 5 else (7, DEFENDER, -20))
                    total += amount
                self.assertEqual(own["amount"], max(0, total))
                counted["tails"] += 1
                if own.get("modifiers"):
                    counted["tails_with_modifiers"] += 1
        self.assertTrue(all(counted[k] > 0 for k in ("heads", "tails", "tails_with_modifiers")), counted)

    def test_knock_outs_prizes_promotions_and_results(self):
        """きぜつ → サイド（きぜつしたポケモンの相手側。同時なら番のプレイヤーから）→ 判定 → バトル場（番でないプレイヤーから）。"""
        counted = Counter()
        for seed, (state, _) in self.games.items():
            for attack, events in attacks(state):
                ko = [e for e in events if e["kind"] == "knock_out"]
                if not ko:
                    continue
                takers = [e["player"] for e in events if e["kind"] == "take_prize"]
                expected = [1 - e["player"] for e in ko]  # 相手のポケモンのきぜつ（番のプレイヤーが取る）が先
                self.assertEqual(takers, expected[:len(takers)], (seed, attack))
                self.assertEqual([e.get("simultaneous", False) for e in ko], [len(ko) > 1] * len(ko))
                if any(e["player"] == attack["player"] for e in ko):
                    counted["self_knock_out"] += 1
                if len(ko) > 1:
                    counted["simultaneous"] += 1
                    promoted = [e["player"] for e in events if e["kind"] == "promote_active"]
                    if len(promoted) == 2:
                        self.assertEqual(promoted, [1 - attack["player"], attack["player"]])
                        counted["both_promoted"] += 1
            if state.phase is Phase.SUDDEN_DEATH:
                counted["sudden_death"] += 1
            # 最後の状態から、表の判定をやり直しても同じ結果
            recomputed = judge.decide(
                all_prizes_taken=[not p.prizes for p in state.players],
                cannot_field_active=[p.active is None and not p.bench for p in state.players],
            )
            if state.result.conditions[0][1] != "OPPONENT_DECK_EMPTY":
                self.assertEqual(recomputed, state.result, seed)
        self.assertTrue(all(counted[k] > 0 for k in ("self_knock_out", "simultaneous", "both_promoted", "sudden_death")), counted)

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed in (0, 9):
            with self.subTest(seed=seed):
                state, commands = self.games[seed]
                replayed = new_game(PIKACHU_DECK, PIKACHU_DECK_B, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual(full(replayed), full(state))
                self.assertEqual(play_game(seed)[1], commands)

    def test_only_coins_use_randomness_after_setup(self):
        for seed, (state, _) in self.games.items():
            expected = copy_rng(new_game(PIKACHU_DECK, PIKACHU_DECK_B, seed).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), seed)


class GoldenSuddenDeathGameTest(unittest.TestCase):
    """seed 9 の対戦は、でんげきの同時のきぜつで両方が最後のサイドを取り、サドン・デスになる。結果を固定値と比べる
    （Python 3.11・3.12・3.13 で同じ値になることを確かめた。v0.2f）。効果の登録表の id は版の名前なので、ハッシュから除く。"""

    def test_seed_9(self):
        state, commands = play_game(9)
        self.assertEqual((len(commands), state.turn_number, state.phase), (193, 79, Phase.SUDDEN_DEATH))
        self.assertEqual(state.result.conditions, ((0, "ALL_PRIZES_TAKEN"), (1, "ALL_PRIZES_TAKEN")))
        data = full(state)
        # v0.69・v0.97: 写しの元を上げた（7d3f4ca・73a1690）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, GOLDEN_SEED_9)


GOLDEN_SEED_9 = "bd11cde2dc86b8bf3f63bcf3e38a90fde0e95f8a0bcbdfc329287bf03f509fd5"


class RandomCommandsWithPikachuTest(unittest.TestCase):
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
            others = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0, -1, 999]
            return ResolveDecision(r.choice([d.player, 1 - d.player]), r.choice([d.id, d.id + 1, d.id - 1]),
                                   tuple(r.choice(list(d.options) + others) for _ in range(r.randint(0, 2))))
        if kind == 2:
            return Retreat(player, (), r.choice(uids))
        if kind == 3:
            return AttachEnergy(player, r.choice(uids), r.choice(uids))
        if kind == 4:
            return UseAttack(player, r.choice([0, 1, 1, 2, -1]))
        return EndTurn(player)

    def test_random_commands(self):
        counted = Counter()
        for seed in range(12):
            r = random.Random(seed)
            state = new_game(PIKACHU_DECK, PIKACHU_DECK_B, seed)
            for _ in range(300):
                if state.phase in TERMINAL:
                    break
                command = trainer_policy_command(state, janken_winner=seed % 2) if r.random() < 0.5 else self.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError:
                    counted["rejected"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                events = new.log[len(state.log):]
                if any(e["kind"] == "damage" and e.get("target") == "self" for e in events):
                    counted["self_damage"] += 1
                if any(e["kind"] == "knock_out" and e.get("simultaneous") for e in events):
                    counted["simultaneous"] += 1
                state = new
        self.assertGreater(counted["self_damage"], 0)
        self.assertGreater(counted["rejected"], 0)


if __name__ == "__main__":
    unittest.main()
