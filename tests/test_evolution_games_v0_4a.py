"""進化（v0.4a）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

パラス → パラセクト、パウワウ → ジュゴンの 1 進化と、v0.3 までの特殊状態（ビードル・キャタピー・ロコン）・
プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすりを混ぜる。進化の成功・拒否（最初の番・今の番に
出したポケモン）、バトル場・ベンチでの進化、特殊状態・ダメージ・ついているトレーナーのあるポケモンの進化、進化した
ポケモンのワザ・きぜつ・サイドが自然な対戦の中で起こる回数を数えて固定する（docs/evolution-state-v0.4a.md 10 章）。
根拠のページは tests/test_evolution_v0_4a.py（p.309・p.310・p.313・p.319・p.322〜324）。

手順は test_confusion_games.py の ``confusion_policy_command`` に、進化（``evolution_command``）と、パラセクト・
ジュゴンのワザの選び方を加えたもの（対戦相手の AI ではない）。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn, EngineError, EvolvePokemon, IllegalActionError, Phase, Retreat, UnsupportedError, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    BILL, CATERPIE, DEFENDER, DEWGONG, FIRE, GRASS, PARAS, PARASECT, PLUSPOWER, POTION, SEEL, SWITCH, VULPIX, WATER, WEEDLE,
    coin_events, expand_decklist,
)
from tests.test_confusion_games import EXPECTED_REJECTIONS, TERMINAL, confusion_policy_command
from tests import test_weedle_games

EVOLUTION_DECK_A = expand_decklist({
    PARAS: 4, PARASECT: 3, SEEL: 4, DEWGONG: 3, WEEDLE: 3, CATERPIE: 2, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2, BILL: 2, POTION: 2,
    GRASS: 17, WATER: 14,
})
EVOLUTION_DECK_B = expand_decklist({
    PARAS: 4, PARASECT: 3, SEEL: 3, DEWGONG: 2, CATERPIE: 3, VULPIX: 3, WEEDLE: 3, DEFENDER: 2, SWITCH: 2, BILL: 2,
    GRASS: 17, FIRE: 8, WATER: 8,
})
CURE_SEEDS = tuple(range(20))
NO_CURE_SEEDS = tuple(range(300, 320))
EVOLUTION_REJECTIONS = ("FIRST_TURN_EVOLUTION", "PLAYED_THIS_TURN")
STAGE1 = (PARASECT, DEWGONG)


def full(state):
    return state_to_dict(state, format_version=7)


def decks(seed):
    return (EVOLUTION_DECK_A, EVOLUTION_DECK_B) if seed % 2 == 0 else (EVOLUTION_DECK_B, EVOLUTION_DECK_A)


def evolution_command(state, *, tried=()):
    """手札の 1 進化カードを、名前の合う自分の場のポケモンに重ねる（バトル場から先）。進化できるポケモンがいなければ、
    名前の合うポケモン（最初の番・今の番に出したもの）に一度だけ試す（拒否されることを確かめる）。なければ None。"""
    player = state.current_player
    p = state.players[player]
    eligible, ineligible = [], []
    for uid in p.hand:
        definition = state.card_def(uid)
        if not definition.is_stage1_pokemon:
            continue
        for target in p.in_play():
            if state.card_def(target.card).name_ja != definition.evolves_from:
                continue
            ok = state.turn_number > 2 and target.current_form_turn < state.turn_number
            (eligible if ok else ineligible).append(EvolvePokemon(player, uid, target.pokemon_id))
    if eligible:
        return eligible[0]
    if ineligible and "evolve" not in tried:
        return ineligible[0]
    return None


def policy_command(state, *, janken_winner, cure, tried):
    command = confusion_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)):
        return command
    evolve = evolution_command(state, tried=tried)
    if evolve is not None:
        return evolve
    if isinstance(command, UseAttack):
        player = state.current_player
        active = state.players[player].active
        card_id = state.cards[active.card].card_id
        opponent = state.players[1 - player].active.conditions
        attacks = state.card_def(active.card).attacks
        # パラセクトはキノコのほうし（0）、ジュゴンはれいとうビーム（1）を、相手がその状態でなく払えるときに使う
        if card_id == PARASECT and not opponent.asleep and can_pay_cost(attacks[0].cost, state.energy_types(active)):
            return UseAttack(player, 0)
        if card_id == DEWGONG and not opponent.paralyzed and can_pay_cost(attacks[1].cost, state.energy_types(active)):
            return UseAttack(player, 1)
    return command


def play_game(seed, *, cure=True, max_steps=6000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・進化の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                if isinstance(command, EvolvePokemon) and error.code in EVOLUTION_REJECTIONS:
                    observed[f"rejected_evolve_{error.code}"] += 1
                    turn_tried.add("evolve")
                    continue
                if error.code not in EXPECTED_REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        if isinstance(command, EvolvePokemon):
            p = state.players[command.player]
            target = p.find_by_pokemon_id(command.target)
            observed["evolve_active" if target is p.active else "evolve_bench"] += 1
            if target.damage:
                observed["evolve_with_damage"] += 1
            if target.trainers:
                observed["evolve_with_trainers"] += 1
            if target.energy:
                observed["evolve_with_energy"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    counted = Counter()
    log = [dict(e) for e in state.log]
    evolved_cards = set()
    for e in log:
        kind = e["kind"]
        if kind == "evolve":
            counted["evolve"] += 1
            counted[f"evolve_to_{e['to_card_id']}"] += 1
            evolved_cards.add(e["to_card"])
        elif kind == "special_conditions_removed" and e["reason"] == "evolve":
            counted["evolve_cleared_" + "+".join(e["conditions"])] += 1
        elif kind == "retreat_failure_cleared":
            counted["evolve_cleared_retreat_failure"] += 1
        elif kind == "attack" and e["pokemon"] in evolved_cards:
            counted["attack_by_evolved"] += 1
            counted[f"attack_by_evolved_{e['attack']}"] += 1
        elif kind == "knock_out" and "evolution_stack" in e:
            counted["knock_out_evolved"] += 1
            if e.get("timing") == "pokemon_check":
                counted["knock_out_evolved_in_check"] += 1
        elif kind == "knock_out":
            counted["knock_out_basic"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithEvolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_counts(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("evolve", "evolve_to_PMCG2-010", "evolve_to_PMCG1-030", "evolve_active", "evolve_bench", "evolve_with_damage",
                    "evolve_with_energy", "attack_by_evolved", "knock_out_evolved", "rejected_evolve_FIRST_TURN_EVOLUTION",
                    "rejected_evolve_PLAYED_THIS_TURN", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_card_conservation_and_prizes(self):
        """どの局も、終わった状態でカードの保存則を満たし、取ったサイドの数ときぜつの数が合う（進化したポケモンも 1 匹で 1 枚）。"""
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertEqual(check_invariants(state), [])
                log = [dict(e) for e in state.log]
                knock_outs = Counter(1 - e["player"] for e in log if e["kind"] == "knock_out")
                prizes = Counter(e["player"] for e in log if e["kind"] == "take_prize")
                for player in (0, 1):
                    # きぜつ 1 匹につきサイド 1 枚（残りがあるかぎり）。重なったカードの数では増えない
                    self.assertEqual(prizes[player], min(knock_outs[player], 6))
                    if any(e["kind"] == "set_prizes" for e in log):  # 対戦準備で止まった局はサイドを置いていない
                        self.assertEqual(len(state.players[player].prizes), 6 - prizes[player])

    def test_games_end_and_replay(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))
        for key in (("cure", 0), ("no_cure", 301)):
            state, commands, _ = self.games[key]
            replayed = new_game(*decks(key[1]), key[1])
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))

    def test_only_coins_use_randomness_after_setup(self):
        """進化は乱数を使わない。対戦準備のあとの乱数はコインだけ。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)

    def test_evolved_pokemon_cards_are_traceable(self):
        """進化したポケモンのきぜつのログの ``evolution_stack`` と ``pokemon`` は、その局の ``evolve`` のログと合う。"""
        for key, (state, _, _) in self.games.items():
            log = [dict(e) for e in state.log]
            evolved = {e["to_card"]: e["from_card"] for e in log if e["kind"] == "evolve"}
            for e in log:
                if e["kind"] == "knock_out" and "evolution_stack" in e:
                    self.assertEqual(e["evolution_stack"], (evolved[e["pokemon"]],), key)
                    self.assertIn(e["pokemon"], state.players[e["player"]].discard + state.players[e["player"]].hand
                                  + state.players[e["player"]].deck, key)


class GoldenEvolutionGameTest(unittest.TestCase):
    """進化が起こる対戦（cure seed GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.4a）。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        self.assertGreater(counted["evolve"], 0)
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.12")  # v0.4b・v0.4c・v0.4d・v0.5・v0.6・v0.7・v0.8・v0.9・v0.10・v0.11・v0.12 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class RandomCommandsWithEvolutionTest(unittest.TestCase):
    """正しい手順・でたらめな操作・でたらめな進化を混ぜる（固定 seed）。拒否は状態も乱数も変えない。"""

    def random_evolve(self, r, state):
        uids = list(state.cards) + [-1, 999]
        ids = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0, 999]
        player = r.choice([0, 1, 0, 1, 2])
        hand = state.players[player].hand if player in (0, 1) else []
        card = r.choice([u for u in hand if state.card_def(u).category == "pokemon"] or uids) if r.random() < 0.7 else r.choice(uids)
        return EvolvePokemon(player, card, r.choice(ids))

    def test_random_commands(self):
        generator = test_weedle_games.RandomCommandsWithWeedleTest()
        counted = Counter()
        for seed in range(12):
            r = random.Random(seed)
            state = new_game(*decks(seed), seed)
            for _ in range(400):
                if state.phase in TERMINAL:
                    counted[f"ended_{state.phase.value}"] += 1
                    break
                roll = r.random()
                if roll < 0.5:
                    command = policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0, tried=())
                elif roll < 0.75:
                    command = self.random_evolve(r, state)
                elif roll < 0.85 and state.phase is Phase.MAIN and state.players[state.current_player].bench:
                    p = state.players[state.current_player]
                    cost = state.card_def(p.active.card).retreat_cost
                    command = Retreat(state.current_player, tuple(p.active.energy[:cost]), r.choice(p.bench).card)
                else:
                    command = generator.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted["rejected"] += 1
                    counted[f"rejected_{type(command).__name__}_{error.code}"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                for e in new.log[len(state.log):]:
                    counted[e["kind"]] += 1
                state = new
        for key in ("rejected", "evolve", "rejected_EvolvePokemon_NOT_EVOLUTION_CARD", "rejected_EvolvePokemon_CARD_NOT_IN_HAND",
                    "rejected_EvolvePokemon_EVOLUTION_NAME_MISMATCH"):
            self.assertGreater(counted[key], 0, (key, counted))


# 自然な対戦（CURE_SEEDS の 20 局・NO_CURE_SEEDS の 20 局）で数えた回数（v0.4a）。手順・デッキ・乱数の使い方が変わると変わる。
# 止まった 4 局は、どれも対戦準備の切り直しの補償（v0.1 からの未解決）。こんらん・にげるの失敗の記録からの進化は、この
# 40 局では起こらない（単体テストで確かめる）
EXPECTED_COUNTS = {
    "evolve": 230, "evolve_to_PMCG2-010": 124, "evolve_to_PMCG1-030": 106, "evolve_active": 47, "evolve_bench": 183,
    "evolve_with_damage": 31, "evolve_with_energy": 98, "evolve_with_trainers": 4,
    "evolve_cleared_paralysis": 4, "evolve_cleared_poison": 2, "evolve_cleared_sleep": 3,
    "rejected_evolve_FIRST_TURN_EVOLUTION": 28, "rejected_evolve_PLAYED_THIS_TURN": 85,
    "attack_by_evolved": 197, "attack_by_evolved_キノコのほうし": 103, "attack_by_evolved_きりさく": 60,
    "attack_by_evolved_オーロラビーム": 10, "attack_by_evolved_れいとうビーム": 24,
    "knock_out_evolved": 62, "knock_out_evolved_in_check": 23, "knock_out_basic": 196, "take_prize": 258,
    "rejected_attack_POKEMON_ASLEEP": 85, "rejected_attack_POKEMON_PARALYZED": 108, "rejected_retreat_POKEMON_ASLEEP": 114,
    "rejected_retreat_POKEMON_PARALYZED": 153, "rejected_retreat_RETREAT_ALREADY_FAILED": 4,
    "phase_game_over": 36, "phase_halted": 4, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 4,
}
# cure seed 0: 216 コマンド、84 番で勝敗が決まる（進化 9 回: パラセクト 6・ジュゴン 3。ねむりからの進化 1 回）
GOLDEN_SEED = 0
GOLDEN_SHAPE = (216, 84, Phase.GAME_OVER)
GOLDEN_DIGEST = "71ffecdde0e1ab0e0659be96e9324c194d493e88ed352a1912489446b1543903"


if __name__ == "__main__":
    unittest.main()
