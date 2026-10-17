"""ビードル（v0.3a）を入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗が決まるまで。

どくばりでどく状態にし、ポケモンチェックでダメージを与え、にげる・ポケモンいれかえで解除し、どくできぜつさせる
ことが、自然な対戦の中で起こることを確かめる（根拠のページは test_special_conditions.py・test_pokemon_check.py）。

手順は tests/helpers.py の ``trainer_policy_command``（既存の対戦の結果を変えないため、そのまま使う）に、
「自分の対戦ポケモンがどく状態なら、ポケモンいれかえか、にげるでベンチに戻す」を加えたもの（``poison_policy_command``）。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command,
    check_invariants, judge, new_game, state_to_dict,
)
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    driver_retreat_cost,
    BILL, DEFENDER, DIGLETT, DODUO, DRATINI, FIGHTING, GRASS, HITMONCHAN, MACHOP, PLUSPOWER, POTION, RATTATA, SWITCH, WEEDLE,
    coin_events, expand_decklist, trainer_policy_command,
)

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
WEEDLE_DECK = expand_decklist({
    WEEDLE: 4, RATTATA: 4, DODUO: 4, DRATINI: 4, SWITCH: 2, POTION: 2, PLUSPOWER: 2, DEFENDER: 2, BILL: 2, GRASS: 34,
})
WEEDLE_DECK_B = expand_decklist({WEEDLE: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, SWITCH: 2, DEFENDER: 2, GRASS: 20, FIGHTING: 20})
# ビードルのミラー（トレーナーなし。どくを直す手段がない）
WEEDLE_MIRROR = expand_decklist({WEEDLE: 4, RATTATA: 4, DODUO: 4, DRATINI: 4, GRASS: 44})
# どくできぜつして勝敗が決まる対戦（8・13・15・17・20）を含む seed（0〜29 から選んだ）
SEEDS = (0, 1, 3, 8, 13, 15, 17, 20)


def full(state):
    return state_to_dict(state, format_version=5)


def poison_policy_command(state, *, janken_winner=0):
    """自分の対戦ポケモンがどく状態で控えがいれば、ポケモンいれかえ（手札にあれば）か、にげる（にげるエネルギーが
    足りれば）でベンチに戻す（p.311・p.322）。それ以外は ``trainer_policy_command``。"""
    if state.phase is Phase.MAIN:
        player = state.current_player
        p = state.players[player]
        if p.active.conditions.poison is not None and p.bench:
            switch = next((u for u in p.hand if state.cards[u].card_id == SWITCH), None)
            if switch is not None:
                return PlayTrainer(player, switch)
            cost = driver_retreat_cost(state, p.active)
            if len(p.active.energy) >= cost:
                return Retreat(player, tuple(p.active.energy[:cost]), p.bench[0].card)
    return trainer_policy_command(state, janken_winner=janken_winner)


def play_game(seed, max_steps=6000):
    state = new_game(WEEDLE_DECK, WEEDLE_DECK_B, seed)
    commands = []
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands
        command = poison_policy_command(state, janken_winner=seed % 2)
        commands.append(command)
        state = apply_command(state, command)
        problems = check_invariants(state)
        if problems:
            raise AssertionError(problems)
    raise AssertionError("決まった手数で終わらなかった")


def turns(state):
    """番ごとのログ（turn_start から次の turn_start の前まで）。"""
    log = [dict(e) for e in state.log]
    starts = [i for i, e in enumerate(log) if e["kind"] == "turn_start"] + [len(log)]
    return [log[a:b] for a, b in zip(starts, starts[1:])]


class FullGameWithWeedleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed) for seed in SEEDS}

    def test_games_end_with_valid_states(self):
        for seed, (state, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))
                self.assertEqual(check_invariants(state), [])
                if state.phase is Phase.HALTED:
                    self.assertEqual(state.halt.code, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")

    def test_poison_transitions(self):
        """主な状態遷移を実際に通ったことを数える（どくばり・どく状態にする・ポケモンチェック・どくのダメージ・
        どくできぜつ・解除・ポケモンチェックの中で勝敗が決まる）。数は docs/weedle-v0.3a.md に書いた。"""
        counted = Counter()
        for seed, (state, _) in self.games.items():
            log = [dict(e) for e in state.log]
            for i, e in enumerate(log):
                k = e["kind"]
                if k == "attack" and e["attack"] == "どくばり":
                    counted["poison_sting"] += 1
                elif k == "special_condition":
                    counted["poisoned"] += 1
                    # どく状態にするのは、どくばりのコインが「おもて」のときだけ（直前のイベント）
                    self.assertEqual((log[i - 1]["kind"], log[i - 1]["result"], log[i - 1]["effect"]), ("coin_flip", "heads", "PMCG1-004#0"))
                elif k == "pokemon_check":
                    counted["pokemon_check"] += 1
                elif k == "poison_damage":
                    counted["poison_damage"] += 1
                elif k == "knock_out" and e.get("timing") == "pokemon_check":
                    counted["poison_knock_out"] += 1
                elif k == "special_conditions_removed":
                    counted["cured_by_" + e["reason"]] += 1
            if state.phase is Phase.GAME_OVER and state.log[-1]["kind"] == "game_end":
                last_start = max(j for j, e in enumerate(log) if e["kind"] == "turn_start")
                if "pokemon_check" in [e["kind"] for e in log[last_start:]]:
                    counted["decided_in_check"] += 1
        for key in ("poison_sting", "poisoned", "pokemon_check", "poison_damage", "poison_knock_out", "cured_by_retreat", "decided_in_check"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_each_turn_has_one_check_and_poison_damage_only_there(self):
        for seed, (state, _) in self.games.items():
            for events in turns(state):
                kinds = [e["kind"] for e in events]
                if "turn_end" in kinds:
                    self.assertEqual((kinds.count("turn_end"), kinds.count("pokemon_check")), (1, 1), seed)
                    check = kinds.index("pokemon_check")
                    self.assertEqual(kinds.index("turn_end") + 1, check)
                    self.assertTrue(all(i > check for i, k in enumerate(kinds) if k == "poison_damage"), seed)
                else:
                    self.assertNotIn("poison_damage", kinds)

    def test_poison_knock_outs(self):
        """どくできぜつしたら、きぜつしたポケモンの相手側がサイドを取り（番のプレイヤーに固定しない）、持ち主が出す。"""
        owners = Counter()
        for seed, (state, _) in self.games.items():
            for events in turns(state):
                kinds = [e["kind"] for e in events]
                if "pokemon_check" not in kinds:
                    continue
                after = events[kinds.index("pokemon_check"):]
                knocked = [e for e in after if e["kind"] == "knock_out"]
                if not knocked:
                    continue
                self.assertEqual(len(knocked), 1)
                ko = knocked[0]
                self.assertEqual(ko["timing"], "pokemon_check")
                takers = [e["player"] for e in after if e["kind"] == "take_prize"]
                self.assertIn(takers, ([1 - ko["player"]], []))
                promoted = [e["player"] for e in after if e["kind"] == "promote_active"]
                self.assertIn(promoted, ([ko["player"]], []))
                owners["turn_player" if ko["player"] == events[0]["player"] else "other"] += 1
        self.assertGreater(owners["turn_player"] + owners["other"], 0)

    def test_results_match_the_table(self):
        for seed, (state, _) in self.games.items():
            if state.phase is Phase.HALTED or state.result.conditions[0][1] == "OPPONENT_DECK_EMPTY":
                continue
            recomputed = judge.decide(
                all_prizes_taken=[not p.prizes for p in state.players],
                cannot_field_active=[p.active is None and not p.bench for p in state.players],
            )
            self.assertEqual(recomputed, state.result, seed)

    def test_same_seed_and_commands_give_the_same_game(self):
        for seed in (0, 3):
            with self.subTest(seed=seed):
                state, commands = self.games[seed]
                replayed = new_game(WEEDLE_DECK, WEEDLE_DECK_B, seed)
                for command in commands:
                    replayed = apply_command(replayed, command)
                self.assertEqual(full(replayed), full(state))
                self.assertEqual(play_game(seed)[1], commands)

    def test_only_coins_use_randomness_after_setup(self):
        """対戦準備のあと乱数を使うのはコインだけ（どくのダメージ・ポケモンチェック・きぜつは乱数を使わない）。"""
        for seed, (state, _) in self.games.items():
            expected = copy_rng(new_game(WEEDLE_DECK, WEEDLE_DECK_B, seed).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), seed)


class GoldenPoisonGameTest(unittest.TestCase):
    """どくできぜつして勝敗が決まる対戦（ポケモンチェックの中で決まる）の結果を固定値と比べる（Python 3.11・3.12・3.13
    で同じ値になることを確かめた。v0.3a）。効果の登録表の id は版の名前なので、ハッシュから除く。"""

    def test_seed(self):
        state, commands = play_game(GOLDEN_SEED)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        self.assertEqual(state.result.conditions, ((0, "OPPONENT_CANNOT_FIELD_ACTIVE"),))
        self.assertEqual([e["kind"] for e in state.log[-4:]][-2:], ["take_prize", "game_end"])
        self.assertIn("pokemon_check", [e["kind"] for e in state.log[-8:]])
        data = full(state)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, GOLDEN_DIGEST)


class NaturalDoubleKnockOutTest(unittest.TestCase):
    """どくを直さない手順のビードルのミラー（WEEDLE_MIRROR）では、両方の対戦ポケモンがどく状態になり、同じポケモンチェックで
    両方がきぜつする場面が自然に起こる（seed 0〜399 のうち 27・34・47・292・320・332）。原典で決められないので、ダメージを
    与える前に止める（docs/pokemon-check-v0.3a.md 3 章）。"""

    def test_seed_27(self):
        state = new_game(WEEDLE_MIRROR, WEEDLE_MIRROR, 27)
        for _ in range(4000):
            if state.phase in TERMINAL:
                break
            state = apply_command(state, trainer_policy_command(state, janken_winner=1))
        self.assertEqual((state.phase, state.halt.code, state.result), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", None))
        self.assertEqual([e["kind"] for e in state.log[-3:]], ["turn_end", "pokemon_check", "halted"])
        for p in state.players:  # 両方ともどく状態で、どくのダメージを足すと HP 以上（まだ与えていない）
            self.assertIsNotNone(p.active.conditions.poison)
            self.assertGreaterEqual(p.active.damage + p.active.conditions.poison.damage, state.card_def(p.active.card).hp)
            self.assertLess(p.active.damage, state.card_def(p.active.card).hp)
        self.assertEqual(check_invariants(state), [])
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, EndTurn(1 - state.current_player))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")


class RandomCommandsWithWeedleTest(unittest.TestCase):
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
            active = state.players[player].active if player in (0, 1) else None
            discard = tuple(active.energy[:1]) if active is not None and r.random() < 0.5 else ()
            return Retreat(player, discard, r.choice(uids))
        if kind == 3:
            return AttachEnergy(player, r.choice(uids), r.choice(uids))
        if kind == 4:
            return UseAttack(player, r.choice([0, 0, 1, -1]))
        return EndTurn(player)

    def test_random_commands(self):
        counted = Counter()
        for seed in range(12):
            r = random.Random(seed)
            state = new_game(WEEDLE_DECK, WEEDLE_DECK_B, seed)
            for _ in range(300):
                if state.phase in TERMINAL:
                    break
                command = poison_policy_command(state, janken_winner=seed % 2) if r.random() < 0.5 else self.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError:
                    counted["rejected"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                events = [e["kind"] for e in new.log[len(state.log):]]
                counted["poison_damage"] += events.count("poison_damage")
                counted["poisoned"] += events.count("special_condition")
                state = new
        self.assertGreater(counted["rejected"], 0)
        self.assertGreater(counted["poisoned"], 0)
        self.assertGreater(counted["poison_damage"], 0)


# 自然な対戦（SEEDS の 8 局）で数えた回数（v0.3a）。手順・デッキ・乱数の使い方が変わると変わる
EXPECTED_COUNTS = {
    "pokemon_check": 262, "poison_sting": 69, "poisoned": 36, "poison_damage": 40, "cured_by_retreat": 22, "cured_by_switch": 1,
    "poison_knock_out": 13, "decided_in_check": 5,
}
# seed 13: 38 コマンド、10 番目の番のあとのポケモンチェックで、プレイヤー 1 のポケモンがどくできぜつし、代わりを出せずに負ける
GOLDEN_SEED = 13
GOLDEN_SHAPE = (38, 10, Phase.GAME_OVER)
GOLDEN_DIGEST = "c2257770c86e91b9984298270dd03f65706ad63d7b12f2c7c75c827368bb7966"


if __name__ == "__main__":
    unittest.main()
