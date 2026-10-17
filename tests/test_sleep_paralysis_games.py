"""キャタピー・パラス（v0.3b）を入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗が決まるまで。

いとをはくでマヒ・キノコのほうしでねむりにし、ワザ・にげるが拒否され、ポケモンチェックでねむりのコインを投げ、マヒが
持ち主の次の番の終わりに回復し、どく（ビードル）と重なり、ポケモンいれかえで消え、どくできぜつすることが、自然な対戦の中で
起こることを確かめる（根拠のページは test_sleep_paralysis.py・test_pokemon_check_v0_3b.py・test_caterpie_paras.py）。

手順（``status_policy_command``）は tests/helpers.py の ``trainer_policy_command`` に次を加えたもの（対戦相手の AI ではない）:

- 自分の対戦ポケモンが特殊状態なら、ポケモンいれかえ（手札にあれば）でベンチに戻す。どくだけなら、にげるでもよい
  （``cure=False`` の対戦ではしない。どくが重なり、どくできぜつしやすい）
- 自分の対戦ポケモンがねむり・マヒなら、その番に 1 回ずつ、にげる・ワザを試す（拒否されることを数える。拒否された操作は
  状態を変えないので、操作の列には入れない）
- 相手の対戦ポケモンにない特殊状態（どく／ねむり・マヒ）を与えられるポケモンがベンチにいれば、にげるで入れ替える。
  バトル場のポケモンがワザを全部使えるなら、エネルギーはベンチのそのポケモンにつける
- パラスは、相手がねむりでなければキノコのほうし、ねむりならひっかく
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, IllegalActionError, Phase, PlayTrainer, Retreat, UseAttack, apply_command,
    can_pay_cost, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    driver_retreat_cost,
    BILL, CATERPIE, DEFENDER, DIGLETT, FIGHTING, GRASS, PARAS, PLUSPOWER, POTION, RATTATA, SWITCH, WEEDLE, coin_events,
    energy_in_hand, expand_decklist, trainer_policy_command,
)
from tests.test_weedle_games import RandomCommandsWithWeedleTest

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
RESTRICTED = ("POKEMON_ASLEEP", "POKEMON_PARALYZED")
STATUS_DECK_A = expand_decklist({
    CATERPIE: 4, PARAS: 4, WEEDLE: 4, RATTATA: 4, SWITCH: 2, POTION: 2, PLUSPOWER: 2, DEFENDER: 2, BILL: 2, GRASS: 34,
})
STATUS_DECK_B = expand_decklist({PARAS: 4, CATERPIE: 4, WEEDLE: 4, DIGLETT: 4, SWITCH: 2, DEFENDER: 2, GRASS: 24, FIGHTING: 16})
# どくを直す（cure=True）対戦の seed と、直さない対戦の seed（どく + マヒが重なる 70・290、ねむりがマヒに置きかわり、
# どく + ねむりがポケモンいれかえで消える 141。0〜149 から選んだ）
CURE_SEEDS = tuple(range(12))
NO_CURE_SEEDS = (70, 141, 290)
# 特殊状態にするワザ（ワザの位置と、与える特殊状態の種類）
STATUS_ATTACK = {WEEDLE: (0, "poison"), CATERPIE: (0, "exclusive"), PARAS: (1, "exclusive")}


def full(state):
    return state_to_dict(state, format_version=5)


def decks(seed):
    return (STATUS_DECK_A, STATUS_DECK_B) if seed % 2 == 0 else (STATUS_DECK_B, STATUS_DECK_A)


def _status_attack(state, pokemon):
    entry = STATUS_ATTACK.get(state.cards[pokemon.card].card_id)
    if entry is None:
        return None
    index, kind = entry
    return index, kind, can_pay_cost(state.card_def(pokemon.card).attacks[index].cost, state.energy_types(pokemon))


def _rotation_command(state):
    """相手にない特殊状態を与えられるポケモンへの入れ替え・エネルギー（決まった手順）。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    opponent = state.players[1 - player].active.conditions
    wanted = {kind for kind, missing in (("poison", opponent.poison is None), ("exclusive", opponent.exclusive is None)) if missing}
    if state.energy_attachments_this_turn == 0 and energy_in_hand(state, player):
        definition = state.card_def(active.card)
        if all(can_pay_cost(a.cost, state.energy_types(active)) for a in definition.attacks if a.supported):
            for benched in p.bench:
                info = _status_attack(state, benched)
                if info is not None and not info[2]:
                    return AttachEnergy(player, energy_in_hand(state, player)[0], benched.card)
    if active.conditions.asleep or active.conditions.paralyzed or not wanted:
        return None
    mine = _status_attack(state, active)
    if mine is not None and mine[1] in wanted and mine[2]:
        return None
    cost = driver_retreat_cost(state, active)
    if len(active.energy) < cost:
        return None
    for benched in p.bench:
        info = _status_attack(state, benched)
        if info is not None and info[1] in wanted and info[2]:
            return Retreat(player, tuple(active.energy[:cost]), benched.card)
    return None


def status_policy_command(state, *, janken_winner=0, cure=True, tried=()):
    """モジュールの説明の手順。``tried``: この番にもう試して拒否された操作の種類（"attack"・"retreat"）。"""
    if state.phase is not Phase.MAIN:
        return trainer_policy_command(state, janken_winner=janken_winner)
    player = state.current_player
    p = state.players[player]
    active = p.active
    restricted = active.conditions.asleep or active.conditions.paralyzed
    cost = driver_retreat_cost(state, active)
    if cure and active.conditions.names() and p.bench:
        switch = next((u for u in p.hand if state.cards[u].card_id == SWITCH), None)
        if switch is not None:
            return PlayTrainer(player, switch)
        if active.conditions.poison is not None and not restricted and len(active.energy) >= cost:
            return Retreat(player, tuple(active.energy[:cost]), p.bench[0].card)
    if restricted and "retreat" not in tried and p.bench and len(active.energy) >= cost:
        return Retreat(player, tuple(active.energy[:cost]), p.bench[0].card)  # 拒否されることを確かめる
    rotation = _rotation_command(state)
    if rotation is not None:
        return rotation
    command = trainer_policy_command(state, janken_winner=janken_winner)
    if isinstance(command, UseAttack):
        if restricted and "attack" in tried:
            return EndTurn(player)
        if state.cards[active.card].card_id == PARAS:
            spore = state.card_def(active.card).attacks[1]
            if not state.players[1 - player].active.conditions.asleep and can_pay_cost(spore.cost, state.energy_types(active)):
                return UseAttack(player, 1)
    return command


def play_game(seed, *, cure=True, max_steps=6000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・重なった特殊状態の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried, overlaps = [], Counter(), {}, set()
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            observed["overlap_poison_sleep"] = sum(1 for _, name in overlaps if name == "sleep")
            observed["overlap_poison_paralysis"] = sum(1 for _, name in overlaps if name == "paralysis")
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = status_policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except IllegalActionError as error:
                if error.code not in RESTRICTED:
                    raise
                observed[f"rejected_{'attack' if isinstance(command, UseAttack) else 'retreat'}_{error.code}"] += 1
                turn_tried.add("attack" if isinstance(command, UseAttack) else "retreat")
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        for p in new.players:
            if p.active is not None and p.active.conditions.poison is not None and p.active.conditions.exclusive is not None:
                overlaps.add((p.active.pokemon_id, p.active.conditions.exclusive.name))
        for e in new.log[len(state.log):]:
            # ねむり・マヒのポケモンがポケモンチェックのどくできぜつした（きぜつしたポケモンのねむりのコインは投げない）
            if e["kind"] == "knock_out" and e.get("timing") == "pokemon_check":
                knocked = state.players[e["player"]].active
                if knocked is not None and knocked.card == e["pokemon"] and knocked.conditions.exclusive is not None:
                    observed[f"poison_knock_out_while_{knocked.conditions.exclusive.name}"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def replay_commands(seed, commands):
    state = new_game(*decks(seed), seed)
    for command in commands:
        state = apply_command(state, command)
    return state


def turns(state):
    log = [dict(e) for e in state.log]
    starts = [i for i, e in enumerate(log) if e["kind"] == "turn_start"] + [len(log)]
    return [log[a:b] for a, b in zip(starts, starts[1:])]


def count_events(state):
    counted = Counter()
    log = [dict(e) for e in state.log]
    for e in log:
        kind = e["kind"]
        if kind == "special_condition":
            counted[f"applied_{e['condition']}" + ("_already" if e.get("already") else "")] += 1
        elif kind == "special_conditions_removed":
            counted[f"removed_{'+'.join(e['conditions'])}_{e['reason']}"] += 1
        elif kind == "sleep_check":
            counted["sleep_recovered" if e["recovered"] else "sleep_continued"] += 1
        elif kind == "knock_out" and e.get("timing") == "pokemon_check":
            counted["poison_knock_out"] += 1
    if state.phase is Phase.GAME_OVER:
        last_start = max(j for j, e in enumerate(log) if e["kind"] == "turn_start")
        if "pokemon_check" in [e["kind"] for e in log[last_start:]]:
            counted["decided_in_check"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    return counted


class FullGameWithSleepAndParalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_games_end_with_valid_states(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertEqual(state.phase, Phase.GAME_OVER)
                self.assertEqual(check_invariants(state), [])

    def test_transitions(self):
        """主な状態遷移を実際に通った回数（docs/sleep-paralysis-v0.3b.md 8 章に書いた）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("applied_sleep", "applied_paralysis", "rejected_attack_POKEMON_ASLEEP", "rejected_attack_POKEMON_PARALYZED",
                    "rejected_retreat_POKEMON_ASLEEP", "rejected_retreat_POKEMON_PARALYZED", "sleep_recovered", "sleep_continued",
                    "removed_paralysis_paralysis_end", "removed_sleep_switch", "removed_paralysis_switch", "overlap_poison_sleep",
                    "overlap_poison_paralysis", "poison_knock_out", "decided_in_check", "removed_sleep_replaced",
                    "removed_poison+sleep_switch", "poison_knock_out_while_sleep", "poison_knock_out_while_paralysis"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_each_check_flips_at_most_one_sleep_coin_after_the_poison(self):
        """番と番のあいだに番の終わり・ポケモンチェックが 1 回ずつ。ねむりのコイン（source pokemon_check）は、ポケモンチェックの
        あとで、どくのダメージ・きぜつ・交代より後、1 回のポケモンチェックに 1 枚まで（両方がねむりにはならない）。"""
        for key, (state, _, _) in self.games.items():
            for events in turns(state):
                kinds = [e["kind"] for e in events]
                check_coins = [i for i, e in enumerate(events) if e["kind"] == "coin_flip" and e["source"] == "pokemon_check"]
                if "turn_end" not in kinds:
                    self.assertEqual(check_coins, [], key)
                    continue
                self.assertEqual((kinds.count("turn_end"), kinds.count("pokemon_check")), (1, 1), key)
                check = kinds.index("pokemon_check")
                self.assertLessEqual(len(check_coins), 1, key)
                for i in check_coins:
                    self.assertGreater(i, check)
                    self.assertEqual(events[i + 1]["kind"], "sleep_check")
                    after_step_2 = [j for j, k in enumerate(kinds) if k in ("poison_damage", "knock_out", "take_prize", "promote_active") and j > check]
                    self.assertTrue(all(j < i for j in after_step_2), key)
                    self.assertEqual(events[i]["player"], events[i + 1]["player"])

    def test_paralysis_recovers_at_the_end_of_the_owners_next_turn(self):
        """マヒ状態にした番（paralyzed_turn）の次の持ち主の番（recovery_turn）の終わりのポケモンチェックで回復している
        （それより前にベンチに戻る・きぜつする・ねむりに置きかわる・対戦が終わる場合を除く）。"""
        checked = 0
        for key, (state, _, _) in self.games.items():
            log = [dict(e) for e in state.log]
            for i, e in enumerate(log):
                if e["kind"] != "special_condition" or e["condition"] != "paralysis" or e.get("already"):
                    continue
                self.assertEqual(e["recovery_turn"], e["turn"] + 1)  # 相手の番にマヒ状態になる（対応カードは相手だけをマヒにする）
                ended = next((x for x in log[i + 1:] if x.get("pokemon_id") == e["pokemon_id"] and x["kind"] == "special_conditions_removed"), None)
                if ended is not None and ended["reason"] == "paralysis_end":
                    self.assertEqual(ended["turn"], e["recovery_turn"], key)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_restricted_pokemon_attacks_are_never_logged(self):
        """ワザ（attack）のログは、ねむり・マヒでないポケモンのワザだけ（拒否された操作は状態を変えないので、ログに残らない）。"""
        for key, (state, commands, _) in list(self.games.items())[:4]:
            replayed = new_game(*decks(key[1]), key[1])
            for command in commands:
                if isinstance(command, (UseAttack, Retreat)):
                    active = replayed.players[command.player].active
                    self.assertFalse(active.conditions.asleep or active.conditions.paralyzed, (key, command))
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))

    def test_same_seed_and_commands_give_the_same_game(self):
        for key in (("cure", 0), ("cure", 5), ("no_cure", 290)):
            with self.subTest(key=key):
                state, commands, _ = self.games[key]
                self.assertEqual(full(replay_commands(key[1], commands)), full(state))
                self.assertEqual(play_game(key[1], cure=key[0] == "cure")[1], commands)

    def test_only_coins_use_randomness_after_setup(self):
        """対戦準備のあと乱数を使うのはコインだけ（ワザのコインとねむりのコイン。マヒの回復・どく・きぜつは乱数を使わない）。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)


class GoldenSleepParalysisGameTest(unittest.TestCase):
    """ねむり・マヒ・どくの起こる対戦（cure seed 6）の結果を固定値と比べる（Python 3.11・3.12・3.13 で同じ値になることを
    確かめた。v0.3b）。効果の登録表の id は版の名前なので、ハッシュから除く。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        self.assertGreater(counted["applied_sleep"], 0)
        self.assertGreater(counted["applied_paralysis"], 0)
        data = full(state)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, GOLDEN_DIGEST)


class NaturalDoubleKnockOutWithStatusDecksTest(unittest.TestCase):
    """どくを直さない手順（no cure seed 127）では、両方の対戦ポケモンが同じポケモンチェックのどくできぜつする場面が自然に
    起こる。v0.3a の未解決のまま、ダメージ・ねむりのコインの前に止める（UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT）。"""

    def test_seed_127(self):
        state, _, _ = play_game(127, cure=False)
        self.assertEqual((state.phase, state.halt.code, state.result), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", None))
        self.assertEqual([e["kind"] for e in state.log[-3:]], ["turn_end", "pokemon_check", "halted"])
        for p in state.players:
            self.assertIsNotNone(p.active.conditions.poison)
            self.assertGreaterEqual(p.active.damage + p.active.conditions.poison.damage, state.card_def(p.active.card).hp)
        self.assertEqual(check_invariants(state), [])


class RandomCommandsWithStatusDecksTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜる（決まった seed。docs/sleep-paralysis-v0.3b.md 9 章の負荷テストの縮小版）。
    拒否は状態も乱数も変えず、受け付けた状態は不変条件を満たす。"""

    def test_random_commands(self):
        generator = RandomCommandsWithWeedleTest()
        counted = Counter()
        for seed in range(16):
            r = random.Random(seed)
            state = new_game(*decks(seed), seed)
            for _ in range(400):
                if state.phase in TERMINAL:
                    counted[f"ended_{state.phase.value}"] += 1
                    break
                if r.random() < 0.6:
                    command = status_policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0)
                else:
                    command = generator.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted["rejected"] += 1
                    counted[f"rejected_{error.code}"] += error.code in RESTRICTED
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                for e in new.log[len(state.log):]:
                    if e["kind"] in ("special_condition", "sleep_check"):
                        counted[e["kind"]] += 1
                state = new
        self.assertGreater(counted["rejected"], 0)
        self.assertGreater(counted["special_condition"], 0)
        self.assertGreater(counted["sleep_check"], 0)
        self.assertGreater(counted["rejected_POKEMON_ASLEEP"] + counted["rejected_POKEMON_PARALYZED"], 0)


# 自然な対戦（CURE_SEEDS の 12 局・NO_CURE_SEEDS の 3 局）で数えた回数（v0.3b）。手順・デッキ・乱数の使い方が変わると変わる
EXPECTED_COUNTS = {
    "applied_sleep": 123, "applied_paralysis": 72, "applied_poison": 58,
    "rejected_attack_POKEMON_ASLEEP": 78, "rejected_attack_POKEMON_PARALYZED": 70,
    "rejected_retreat_POKEMON_ASLEEP": 80, "rejected_retreat_POKEMON_PARALYZED": 70,
    "sleep_recovered": 92, "sleep_continued": 136, "removed_sleep_sleep_coin": 92, "removed_paralysis_paralysis_end": 68,
    "removed_sleep_switch": 8, "removed_paralysis_switch": 2, "removed_poison_switch": 4, "removed_poison+sleep_switch": 1,
    "removed_poison_retreat": 32, "removed_sleep_replaced": 1,
    "overlap_poison_sleep": 4, "overlap_poison_paralysis": 2,
    "poison_knock_out": 17, "poison_knock_out_while_sleep": 2, "poison_knock_out_while_paralysis": 2,
    "decided_in_check": 2, "phase_game_over": 15,
}
# cure seed 6: 156 コマンド、53 番で勝敗が決まる（ねむり 8 回・マヒ 6 回・どく 4 回）
GOLDEN_SEED = 6
GOLDEN_SHAPE = (156, 53, Phase.GAME_OVER)
GOLDEN_DIGEST = "fa99a631c1f9ef6ad2570e430229e9a9f3afe356b9a3d8c290e91f95b7f9b9ab"


if __name__ == "__main__":
    unittest.main()
