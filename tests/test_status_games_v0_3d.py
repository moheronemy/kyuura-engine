"""特殊状態 4 種類と自分へのダメージ・コインのワザを混ぜた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで（v0.3d）。

ビードル（どく）・キャタピー（マヒ）・パラス（ねむり）・ロコン（こんらん）・ピカチュウ（自分へのダメージ）・ドードー
（コイン 2 枚）と、プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすりを入れる。付与・上書き・どくとの
重複・ワザとにげるの制限・こんらんの失敗・ポケモンチェック・解除・きぜつ・サイド・勝敗・止める場合が、自然な対戦の中で
起こる回数を数えて固定する（docs/special-conditions-audit-v0.3d.md 9 章）。根拠のページは
test_special_conditions_matrix_v0_3d.py・test_confusion*.py・test_sleep_paralysis.py・test_special_conditions.py。

手順は test_confusion_games.py の ``confusion_policy_command``（対戦相手の AI ではない）。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import EngineError, IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, new_game, state_to_dict
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    CARD_DATA_COMMIT_SINCE_V0_69,
    with_card_data_commit_before_v0_69,
    BILL, CATERPIE, DEFENDER, DODUO, FIRE, GRASS, LIGHTNING, PARAS, PIKACHU, PLUSPOWER, POTION, SWITCH, VULPIX, WEEDLE,
    coin_events, expand_decklist,
)
from tests.test_confusion_games import EXPECTED_REJECTIONS, TERMINAL, confusion_policy_command
from tests import test_weedle_games

# どちらのデッキにも、どく（ビードル）・ねむり（パラス）・マヒ（キャタピー）・こんらん（ロコン）を入れ、同じ相手のポケモンに
# どくとほかの特殊状態を重ねられるようにした。A にはピカチュウ（自分へのダメージ）とプラスパワー、B にはドードー（コイン 2 枚）
ALL_STATUS_DECK_A = expand_decklist({
    WEEDLE: 3, PARAS: 3, CATERPIE: 3, VULPIX: 3, PIKACHU: 4, SWITCH: 2, PLUSPOWER: 2, DEFENDER: 2, BILL: 2, POTION: 2,
    GRASS: 18, FIRE: 8, LIGHTNING: 8,
})
ALL_STATUS_DECK_B = expand_decklist({
    WEEDLE: 3, PARAS: 3, CATERPIE: 3, VULPIX: 3, DODUO: 4, SWITCH: 2, BILL: 2, DEFENDER: 2, GRASS: 22, FIRE: 16,
})
CURE_SEEDS = tuple(range(20))
NO_CURE_SEEDS = tuple(range(300, 324))


def full(state):
    return state_to_dict(state, format_version=6)


def decks(seed):
    return (ALL_STATUS_DECK_A, ALL_STATUS_DECK_B) if seed % 2 == 0 else (ALL_STATUS_DECK_B, ALL_STATUS_DECK_A)


def play_game(seed, *, cure=True, max_steps=6000):
    state = new_game(*decks(seed), seed)
    commands, observed, tried, overlaps = [], Counter(), {}, set()
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            for pokemon_id, name in overlaps:
                observed[f"overlap_poison_{name}"] += 1
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = confusion_policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                if error.code not in EXPECTED_REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        for p in new.players:
            if p.active is not None and p.active.conditions.poison is not None and p.active.conditions.exclusive is not None:
                overlaps.add((p.active.pokemon_id, p.active.conditions.exclusive.name))
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    counted = Counter()
    log = [dict(e) for e in state.log]
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "special_condition":
            counted[f"applied_{e['condition']}" + ("_already" if e.get("already") else "")] += 1
        elif kind == "special_conditions_removed":
            counted[f"removed_{'+'.join(e['conditions'])}_{e['reason']}"] += 1
        elif kind == "confusion_check":
            counted[f"confusion_{e['action']}_{'success' if e['succeeded'] else 'failure'}"] += 1
        elif kind == "confusion_damage":
            counted["confusion_damage"] += 1
        elif kind == "retreat_failed":
            counted["retreat_failed"] += 1
        elif kind == "sleep_check":
            counted["sleep_recovered" if e["recovered"] else "sleep_continued"] += 1
        elif kind == "damage" and e.get("target") == "self":
            counted["attack_self_damage"] += 1
        elif kind == "knock_out":
            counted["knock_out_in_check" if e.get("timing") == "pokemon_check" else "knock_out_after_attack"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithAllConditionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_transitions(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("applied_poison", "applied_sleep", "applied_paralysis", "applied_confusion", "removed_poison+paralysis_switch",
                    "overlap_poison_sleep", "overlap_poison_paralysis", "overlap_poison_confusion",
                    "rejected_attack_POKEMON_ASLEEP", "rejected_attack_POKEMON_PARALYZED", "rejected_retreat_POKEMON_ASLEEP",
                    "rejected_retreat_POKEMON_PARALYZED", "confusion_attack_failure", "confusion_attack_success",
                    "confusion_retreat_failure", "confusion_retreat_success", "rejected_retreat_RETREAT_ALREADY_FAILED",
                    "sleep_recovered", "sleep_continued", "removed_paralysis_paralysis_end", "attack_self_damage",
                    "knock_out_in_check", "knock_out_after_attack", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_games_end_and_replay(self):
        for key, (state, commands, _) in self.games.items():
            with self.subTest(key=key):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))
                if state.phase is Phase.HALTED:
                    self.assertIn(state.halt.code, ("UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"))
        for key in (("cure", 0), ("no_cure", 305)):
            state, commands, _ = self.games[key]
            replayed = new_game(*decks(key[1]), key[1])
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))

    def test_only_coins_use_randomness_after_setup(self):
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)

    def test_one_check_per_turn_and_no_expired_paralysis(self):
        """番と番のあいだに番の終わり・ポケモンチェックが 1 回ずつ（v0.3a の不変条件）。マヒは回復する番を過ぎて残らない。"""
        for key, (state, _, _) in self.games.items():
            log = [dict(e) for e in state.log]
            starts = [i for i, e in enumerate(log) if e["kind"] == "turn_start"]
            for a, b in zip(starts, starts[1:]):
                between = [e["kind"] for e in log[a:b] if e["kind"] in ("turn_end", "pokemon_check")]
                self.assertEqual(between, ["turn_end", "pokemon_check"], key)
            for e in log:
                if e["kind"] == "special_condition" and e["condition"] == "paralysis" and not e.get("already"):
                    ended = next((x for x in log if x.get("pokemon_id") == e["pokemon_id"] and x["kind"] == "special_conditions_removed"
                                  and x["turn"] >= e["turn"]), None)
                    if ended is not None and ended["reason"] == "paralysis_end":
                        self.assertEqual(ended["turn"], e["recovery_turn"])


class GoldenAllConditionsGameTest(unittest.TestCase):
    """4 種類の特殊状態が起こる対戦（cure seed GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.3d）。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for condition in ("poison", "sleep", "paralysis", "confusion"):
            self.assertGreater(counted[f"applied_{condition}"], 0, condition)
        data = full(state)
        # v0.69: 写しの元を上げた（7d3f4ca）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT_SINCE_V0_69)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class RandomCommandsWithAllConditionsTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜる（固定 seed。docs/special-conditions-audit-v0.3d.md 10 章の負荷テストの縮小版）。"""

    def test_random_commands(self):
        from kyuura_engine import Retreat

        generator = test_weedle_games.RandomCommandsWithWeedleTest()  # でたらめな操作を作る道具だけを使う
        counted = Counter()
        for seed in range(12):
            r = random.Random(seed)
            state = new_game(*decks(seed), seed)
            for _ in range(400):
                if state.phase in TERMINAL:
                    counted[f"ended_{state.phase.value}"] += 1
                    break
                if r.random() < 0.6:
                    command = confusion_policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0)
                elif r.random() < 0.3 and state.phase is Phase.MAIN and state.players[state.current_player].bench:
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
                    counted[f"rejected_{error.code}"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                for e in new.log[len(state.log):]:
                    counted[e["kind"]] += 1
                state = new
        for key in ("rejected", "special_condition", "confusion_check", "sleep_check", "retreat_failed",
                    "rejected_POKEMON_ASLEEP", "rejected_POKEMON_PARALYZED"):
            self.assertGreater(counted[key], 0, key)


# 自然な対戦（CURE_SEEDS の 20 局・NO_CURE_SEEDS の 24 局）で数えた回数（v0.3d）。手順・デッキ・乱数の使い方が変わると変わる。
# 止まった局（HALTED）はない。ねむり・マヒ・こんらんのあいだの置きかえは、この 44 局では起こらない（単体テストで確かめる）
EXPECTED_COUNTS = {
    "applied_poison": 123, "applied_poison_already": 1, "applied_sleep": 271, "applied_paralysis": 142,
    "applied_confusion": 68, "applied_confusion_already": 4,
    "overlap_poison_sleep": 5, "overlap_poison_paralysis": 4, "overlap_poison_confusion": 1,
    "rejected_attack_POKEMON_ASLEEP": 131, "rejected_attack_POKEMON_PARALYZED": 108,
    "rejected_retreat_POKEMON_ASLEEP": 153, "rejected_retreat_POKEMON_PARALYZED": 135,
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 2, "rejected_retreat_RETREAT_ALREADY_FAILED": 23,
    "confusion_attack_success": 17, "confusion_attack_failure": 23, "confusion_damage": 23,
    "confusion_retreat_success": 20, "confusion_retreat_failure": 26, "retreat_failed": 26,
    "sleep_recovered": 229, "sleep_continued": 225, "removed_sleep_sleep_coin": 229, "removed_paralysis_paralysis_end": 132,
    "removed_poison_retreat": 51, "removed_confusion_retreat": 20,
    "removed_poison_switch": 5, "removed_sleep_switch": 8, "removed_paralysis_switch": 6, "removed_confusion_switch": 8,
    "removed_poison+paralysis_switch": 1,
    "attack_self_damage": 14, "knock_out_after_attack": 269, "knock_out_in_check": 52,
    "phase_game_over": 44,
}
# cure seed 2: 230 コマンド、87 番で勝敗が決まる（ねむり 24・どく 3・こんらん 4・マヒ 1 回。どく + ねむりが重なる）
GOLDEN_SEED = 2
GOLDEN_SHAPE = (230, 87, Phase.GAME_OVER)
GOLDEN_DIGEST = "fe936a7d3163e7bbc2e71fec6dd52b7788df76dc95d8629bc69285982402922f"


if __name__ == "__main__":
    unittest.main()
