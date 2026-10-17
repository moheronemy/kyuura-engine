"""ロコン（v0.3c）を入れた 60 枚のデッキで、正式な対戦開始（new_game）から勝敗が決まるまで。

あやしいひかりでこんらんにし、こんらんのポケモンのワザでコインを投げ（「うら」なら自分に 20、自分のきぜつ）、にげるでコインを
投げ（「うら」ならエネルギーを失い、同じ番には宣言し直せない）、ポケモンいれかえで消え、どく（ビードル）と重なり、ねむり・
マヒ（パラス・キャタピー）と置きかわることが、自然な対戦の中で起こることを確かめる（根拠のページは test_confusion.py・
test_confusion_attacks.py・test_confusion_retreat.py）。

手順（``confusion_policy_command``）は tests/helpers.py の ``trainer_policy_command`` に次を加えたもの（対戦相手の AI ではない）:

- この番に「にげる」に失敗した対戦ポケモンなら、1 回だけ、もう一度にげるを試す（拒否されることを数える。拒否された操作は
  状態を変えないので、操作の列には入れない）。ねむり・マヒでも 1 回ずつ、にげる・ワザを試す（v0.3b と同じ）
- ``cure=True`` の対戦: 対戦ポケモンがこんらんなら、まず「にげる」（コイン）。それでもバトル場にいて、ポケモンいれかえが手札に
  あれば使う。ほかの特殊状態はポケモンいれかえ、どくだけなら、にげる（v0.3b と同じ）。``cure=False`` の対戦では直さない
  （こんらんのままワザを使う）
- 相手の対戦ポケモンにない特殊状態（どく／ねむり・マヒ・こんらん）を与えられるポケモンがベンチにいれば、にげるで入れ替える
- プラスパワー・ディフェンダーをつけたこんらんのポケモンのワザは原典で決められないので拒否される（数える）。その番はワザを
  使わずに番を終える
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, IllegalActionError, Phase, PlayTrainer, Retreat, UnsupportedError, UseAttack,
    apply_command, can_pay_cost, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.effects import DEFAULT_EFFECTS
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    driver_retreat_cost,
    BILL, CATERPIE, DEFENDER, FIRE, GRASS, PARAS, PLUSPOWER, PONYTA, POTION, RATTATA, SWITCH, VULPIX, WEEDLE, coin_events,
    energy_in_hand, expand_decklist, trainer_policy_command,
)
from tests.test_weedle_games import RandomCommandsWithWeedleTest

TERMINAL = (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED)
# 手順が試して拒否されることを確かめる操作のコード（ほかのコードで拒否されたら手順の誤りなので、テストを失敗させる）
EXPECTED_REJECTIONS = {
    "POKEMON_ASLEEP", "POKEMON_PARALYZED", "RETREAT_ALREADY_FAILED", "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS",
    "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED",
}
CONFUSION_DECK_A = expand_decklist({
    VULPIX: 4, WEEDLE: 4, PONYTA: 4, RATTATA: 4, SWITCH: 2, POTION: 2, PLUSPOWER: 2, DEFENDER: 2, BILL: 2, FIRE: 24, GRASS: 10,
})
CONFUSION_DECK_B = expand_decklist({VULPIX: 4, CATERPIE: 4, PARAS: 4, RATTATA: 4, SWITCH: 2, BILL: 2, FIRE: 20, GRASS: 20})
# 特殊状態にするワザ（ワザの位置と、与える特殊状態の種類）
STATUS_ATTACK = {WEEDLE: (0, "poison"), CATERPIE: (0, "exclusive"), PARAS: (1, "exclusive"), VULPIX: (0, "exclusive")}


def full(state):
    return state_to_dict(state, format_version=6)


def decks(seed):
    return (CONFUSION_DECK_A, CONFUSION_DECK_B) if seed % 2 == 0 else (CONFUSION_DECK_B, CONFUSION_DECK_A)


def _in_hand(state, player, card_id):
    return next((u for u in state.players[player].hand if state.cards[u].card_id == card_id), None)


def _status_attack(state, pokemon):
    entry = STATUS_ATTACK.get(state.cards[pokemon.card].card_id)
    if entry is None:
        return None
    index, kind = entry
    return index, kind, can_pay_cost(state.card_def(pokemon.card).attacks[index].cost, state.energy_types(pokemon))


def _rotation_command(state, *, allow_retreat):
    """相手にない特殊状態を与えられるポケモンへの入れ替え・エネルギー（決まった手順。v0.3b の手順にロコンを加えた）。"""
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
    if not allow_retreat or active.conditions.asleep or active.conditions.paralyzed or not wanted:
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


def confusion_policy_command(state, *, janken_winner=0, cure=True, tried=()):
    """モジュールの説明の手順。``tried``: この番にもう試して拒否された操作の種類（"attack"・"retreat"）。"""
    if state.phase is not Phase.MAIN:
        return trainer_policy_command(state, janken_winner=janken_winner)
    player = state.current_player
    p = state.players[player]
    active = p.active
    conditions = active.conditions
    cost = driver_retreat_cost(state, active)
    retreat = Retreat(player, tuple(active.energy[:cost]), p.bench[0].card) if p.bench and len(active.energy) >= cost else None
    can_retreat = retreat is not None and "retreat" not in tried
    if can_retreat and (active.retreat_failed_turn == state.turn_number or conditions.asleep or conditions.paralyzed):
        return retreat  # 拒否されることを確かめる（再宣言の制限・ねむり・マヒ）
    if cure and can_retreat and conditions.confused:
        return retreat  # こんらんのコイン
    switch = _in_hand(state, player, SWITCH)
    if cure and switch is not None and conditions.names() and p.bench:
        return PlayTrainer(player, switch)
    if cure and can_retreat and conditions.poison is not None and conditions.exclusive is None:
        return retreat
    rotation = _rotation_command(state, allow_retreat=can_retreat and active.retreat_failed_turn is None)
    if rotation is not None:
        return rotation
    command = trainer_policy_command(state, janken_winner=janken_winner)
    if isinstance(command, UseAttack):
        if "attack" in tried:
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
            observed["overlap_poison_confusion"] = len(overlaps)
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
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        for p in new.players:
            if p.active is not None and p.active.conditions.poison is not None and p.active.conditions.confused:
                overlaps.add(p.active.pokemon_id)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def replay_commands(seed, commands):
    state = new_game(*decks(seed), seed)
    for command in commands:
        state = apply_command(state, command)
    return state


def count_events(state):
    """ログから数える（docs/confusion-v0.3c.md 7 章）。"""
    counted = Counter()
    log = [dict(e) for e in state.log]
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "attack" and e["attack"] == "あやしいひかり":
            counted["confuse_ray_used"] += 1
        elif kind == "special_condition":
            counted[f"applied_{e['condition']}" + ("_already" if e.get("already") else "")] += 1
        elif kind == "special_conditions_removed":
            counted[f"removed_{'+'.join(e['conditions'])}_{e['reason']}"] += 1
        elif kind == "confusion_check":
            counted[f"confusion_{e['action']}_{'success' if e['succeeded'] else 'failure'}"] += 1
        elif kind == "confusion_damage":
            counted["confusion_damage"] += 1
            ko = next((x for x in log[i + 1:i + 3] if x["kind"] == "knock_out" and x.get("pokemon") == e["pokemon"]), None)
            counted["confusion_self_knock_out"] += ko is not None
        elif kind == "retreat_failed":
            counted["retreat_failed"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 特殊状態を直す（cure=True）対戦の seed と、直さない対戦の seed（こんらんのままワザを使い、自分のきぜつが起こりやすい）。
# 選ばずに続いた範囲をそのまま使う（36 局）
CURE_SEEDS = tuple(range(24))
NO_CURE_SEEDS = tuple(range(100, 112))


class FullGameWithConfusionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_games_end_with_valid_states(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.HALTED))
                if state.phase is Phase.HALTED:
                    self.assertEqual(state.halt.code, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")
                self.assertEqual(check_invariants(state), [])

    def test_transitions(self):
        """主な状態遷移を実際に通った回数（docs/confusion-v0.3c.md 7 章に書いた）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("confuse_ray_used", "applied_confusion", "confusion_attack_success", "confusion_attack_failure",
                    "confusion_damage", "confusion_self_knock_out", "confusion_retreat_success", "confusion_retreat_failure",
                    "retreat_failed", "rejected_retreat_RETREAT_ALREADY_FAILED", "overlap_poison_confusion",
                    "removed_confusion_switch", "removed_confusion_retreat", "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["confusion_attack_failure"], counted["confusion_damage"])
        self.assertEqual(counted["confusion_retreat_failure"], counted["retreat_failed"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_confusion_coins_in_the_log(self):
        """ワザのこんらんのコイン: ``attack`` → ``coin_flip``（source confusion）→ ``confusion_check`` →（「うら」なら）
        ``confusion_damage``。にげる: ``coin_flip`` → ``confusion_check`` → ``retreat``（「おもて」）か ``retreat_failed``（「うら」）。
        こんらんのコインを投げるのは、こんらん状態のバトル場のポケモンの持ち主だけ。"""
        for key, (state, _, _) in self.games.items():
            log = [dict(e) for e in state.log]
            for i, e in enumerate(log):
                if e["kind"] != "confusion_check":
                    continue
                flip = log[i - 1]
                self.assertEqual((flip["kind"], flip["source"], flip["player"], flip["pokemon_id"], flip["result"]),
                                 ("coin_flip", "confusion", e["player"], e["pokemon_id"], e["result"]), key)
                self.assertEqual(e["succeeded"], e["result"] == "heads")
                after = log[i + 1]["kind"]
                if e["action"] == "attack":
                    self.assertEqual(log[i - 2]["kind"], "attack", key)
                    self.assertEqual(after == "confusion_damage", not e["succeeded"], key)
                else:
                    self.assertEqual(after, "retreat" if e["succeeded"] else "retreat_failed", key)

    def test_failed_pokemon_never_retreats_in_the_same_turn(self):
        """「にげる」に失敗したポケモンが、同じ番にもう一度「にげる」をした記録はない（拒否された操作はログに残らない）。"""
        for key, (state, _, _) in self.games.items():
            failed = set()
            for e in state.log:
                if e["kind"] == "turn_start":
                    failed = set()
                elif e["kind"] == "retreat_failed":
                    self.assertNotIn(e["pokemon_id"], failed, key)
                    failed.add(e["pokemon_id"])
                elif e["kind"] == "confusion_check" and e["action"] == "retreat":
                    self.assertNotIn(e["pokemon_id"], failed, key)

    def test_same_seed_and_commands_give_the_same_game(self):
        for key in (("cure", 0), ("cure", 7), ("no_cure", 101)):
            with self.subTest(key=key):
                state, commands, _ = self.games[key]
                self.assertEqual(full(replay_commands(key[1], commands)), full(state))
                self.assertEqual(play_game(key[1], cure=key[0] == "cure")[1], commands)

    def test_only_coins_use_randomness_after_setup(self):
        """対戦準備のあと乱数を使うのはコインだけ（ワザのコイン・ねむりのコイン・こんらんのコイン。1 枚 1 回）。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)


class GoldenConfusionGameTest(unittest.TestCase):
    """こんらん・どく・ねむり・マヒの起こる対戦（cure seed GOLDEN_SEED）の結果を固定値と比べる（Python 3.11・3.12・3.13 で
    同じ値になることを確かめた。v0.3c）。効果の登録表の id は版の名前なので、ハッシュから除く。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        self.assertGreater(counted["applied_confusion"], 0)
        self.assertGreater(counted["confusion_attack_failure"] + counted["confusion_retreat_failure"], 0)
        data = full(state)
        self.assertEqual(data.pop("effects"), DEFAULT_EFFECTS.id)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, GOLDEN_DIGEST)


class RandomCommandsWithConfusionDecksTest(unittest.TestCase):
    """正しい操作とでたらめな操作を混ぜる（決まった seed。docs/confusion-v0.3c.md 8 章の負荷テストの縮小版）。
    拒否は状態も乱数も変えず、受け付けた状態は不変条件を満たす。"""

    def random_command(self, r, generator, state):
        if r.random() < 0.3 and state.phase is Phase.MAIN:
            # 形のととのった「にげる」（こんらんのコイン・再宣言の拒否を起こしやすくする）
            p = state.players[state.current_player]
            if p.bench:
                cost = state.card_def(p.active.card).retreat_cost
                return Retreat(state.current_player, tuple(p.active.energy[:cost]), r.choice(p.bench).card)
        return generator.random_command(r, state)

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
                    command = confusion_policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0)
                else:
                    command = self.random_command(r, generator, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted["rejected"] += 1
                    counted[f"rejected_{error.code}"] += error.code in EXPECTED_REJECTIONS
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                self.assertEqual(check_invariants(new), [])
                for e in new.log[len(state.log):]:
                    if e["kind"] in ("confusion_check", "retreat_failed", "confusion_damage"):
                        counted[e["kind"]] += 1
                state = new
        self.assertGreater(counted["rejected"], 0)
        self.assertGreater(counted["confusion_check"], 0)
        self.assertGreater(counted["retreat_failed"], 0)
        self.assertGreater(counted["confusion_damage"], 0)
        self.assertGreater(counted["rejected_RETREAT_ALREADY_FAILED"], 0)


# 自然な対戦（CURE_SEEDS の 24 局・NO_CURE_SEEDS の 12 局）で数えた回数（v0.3c）。手順・デッキ・乱数の使い方が変わると変わる。
# 対戦を止めた（HALTED）局はない（phase_halted がない）。こんらんが消えたあとの再宣言（UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED）
# は、この手順では起こらない（test_confusion_retreat.py で確かめる）
EXPECTED_COUNTS = {
    "confuse_ray_used": 272, "applied_confusion": 82, "applied_confusion_already": 6,
    "applied_sleep": 48, "applied_paralysis": 41, "applied_poison": 39, "applied_poison_already": 1,
    "confusion_attack_success": 14, "confusion_attack_failure": 20, "confusion_damage": 20, "confusion_self_knock_out": 17,
    "confusion_retreat_success": 41, "confusion_retreat_failure": 34, "retreat_failed": 34,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 34, "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 2,
    "rejected_attack_POKEMON_ASLEEP": 19, "rejected_attack_POKEMON_PARALYZED": 32,
    "rejected_retreat_POKEMON_ASLEEP": 21, "rejected_retreat_POKEMON_PARALYZED": 41,
    "overlap_poison_confusion": 3,
    "removed_confusion_retreat": 39, "removed_poison+confusion_retreat": 2, "removed_confusion_switch": 5,
    "removed_confusion_replaced": 1, "removed_poison_retreat": 19, "removed_sleep_sleep_coin": 44, "removed_sleep_switch": 1,
    "removed_paralysis_paralysis_end": 36, "removed_paralysis_switch": 5,
    "phase_game_over": 36,
}
# cure seed 19: 150 コマンド、46 番で勝敗が決まる（こんらん 8 回、ワザのこんらんの「うら」2 回で 2 回とも自分がきぜつ、
# 「にげる」の失敗 4 回）
GOLDEN_SEED = 19
GOLDEN_SHAPE = (150, 46, Phase.GAME_OVER)
GOLDEN_DIGEST = "7bc3ba61f2a1d8e7201de183fd1abdf32e7e99545be153e246b77e078621671b"


if __name__ == "__main__":
    unittest.main()
