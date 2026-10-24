"""ワザによる持続する効果（v0.4b）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

キャタピー → トランセル、ビードル → コクーンの進化と「かたまる」（コインが「おもて」なら、次の相手の番、ダメージを受けない。
ダメージ以外の効果は受ける）を、v0.3 までの特殊状態のワザ（どく・マヒ・ねむり・こんらん）・ピカチュウの自分へのダメージ・
ドードーのコインのダメージ・プラスパワー・ディフェンダー・ポケモンいれかえと混ぜる。「かたまる」の「おもて」「うら」、
ダメージの無効（``damage_prevented``）、無効のあとのダメージ以外の効果、効果の期限切れ・きぜつでの消滅、進化したポケモンの
きぜつが、自然な対戦の中で起こる回数を数えて固定する（docs/harden-v0.4b.md 9 章）。根拠のページは tests/test_harden_v0_4b.py。

自然な対戦では起こらないこと（効果を与えた番にベンチに戻る・進化する）は、単体テスト（盤面を直接作る）で確かめる。

手順は test_evolution_games_v0_4a.py の ``policy_command`` に、トランセル・コクーンのワザの選び方を加えたもの（対戦相手の
AI ではない）。ドードーの「みだれづき」を「ダメージを受けない」ポケモンに使うのは原典で決められない（``UnsupportedError``、
``UNRESOLVED_PREVENTED_COIN_DAMAGE``）ので、拒否されたらその番はワザを使わない。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    EngineError, EvolvePokemon, IllegalActionError, Phase, Retreat, UnsupportedError, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    CARD_DATA_COMMIT,
    with_card_data_commit_before_v0_69,
    BILL, CATERPIE, DEFENDER, DODUO, FIRE, GRASS, KAKUNA, LIGHTNING, METAPOD, PARAS, PIKACHU, PLUSPOWER, POTION, SWITCH,
    VULPIX, WEEDLE, coin_events, expand_decklist,
)
from tests.test_confusion_games import EXPECTED_REJECTIONS, TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS, policy_command as evolution_policy_command
from tests import test_weedle_games

HARDEN_DECK_A = expand_decklist({
    CATERPIE: 4, METAPOD: 4, WEEDLE: 4, KAKUNA: 4, DODUO: 3, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2, BILL: 2, POTION: 2, GRASS: 31,
})
HARDEN_DECK_B = expand_decklist({
    CATERPIE: 3, METAPOD: 3, WEEDLE: 3, KAKUNA: 3, VULPIX: 3, PARAS: 3, PIKACHU: 2, DEFENDER: 2, SWITCH: 2, BILL: 2,
    GRASS: 22, FIRE: 8, LIGHTNING: 4,
})
CURE_SEEDS = tuple(range(20))
NO_CURE_SEEDS = tuple(range(300, 320))
HARDEN_CARDS = (METAPOD, KAKUNA)
# 「ダメージを受けない」ポケモンへのドードーの「みだれづき」は、原典で決められないので拒否される（v0.4b）
REJECTIONS = set(EXPECTED_REJECTIONS) | {"UNRESOLVED_PREVENTED_COIN_DAMAGE"}


def full(state):
    return state_to_dict(state, format_version=8)


def decks(seed):
    return (HARDEN_DECK_A, HARDEN_DECK_B) if seed % 2 == 0 else (HARDEN_DECK_B, HARDEN_DECK_A)


def policy_command(state, *, janken_winner, cure, tried):
    """v0.4a の手順（進化を含む）に、トランセル・コクーンのワザの選び方を加える: ダメージが 30 以上か、偶数番目の自分の番なら
    「かたまる」（払えるとき）、そうでなければ「しびれごな」「どくのこな」（払えるとき）。"""
    command = evolution_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, UseAttack):
        return command
    player = state.current_player
    active = state.players[player].active
    if state.cards[active.card].card_id not in HARDEN_CARDS:
        return command
    attacks = state.card_def(active.card).attacks
    provided = state.energy_types(active)
    harden, powder = (can_pay_cost(a.cost, provided) for a in attacks)
    prefer_harden = active.damage >= 30 or (state.turn_number // 2) % 2 == 0
    if harden and (prefer_harden or not powder):
        return UseAttack(player, 0)
    if powder:
        return UseAttack(player, 1)
    return command


def play_game(seed, *, cure=True, max_steps=6000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作の観測を返す。"""
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
                if error.code not in REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。ダメージの無効のあとの特殊状態は、同じワザ（``attack`` から次の ``turn_end`` まで）の中のもの。"""
    counted = Counter()
    log = [dict(e) for e in state.log]
    evolved_cards, prevented_in_attack, last_attack = set(), False, None
    for e in log:
        kind = e["kind"]
        if kind == "evolve":
            counted["evolve"] += 1
            counted[f"evolve_to_{e['to_card_id']}"] += 1
            evolved_cards.add(e["to_card"])
        elif kind == "attack":
            prevented_in_attack, last_attack = False, e["attack"]
            if e["attack"] == "かたまる":
                counted["harden"] += 1
        elif kind == "confusion_check" and e["action"] == "attack" and not e["succeeded"] and last_attack == "かたまる":
            counted["harden_confusion_failed"] += 1  # こんらんのコインが「うら」: 「かたまる」のコインは投げない（p.309 の手順 5）
        elif kind == "coin_flip" and e["source"] == "attack" and e["effect"] in (f"{METAPOD}#0", f"{KAKUNA}#0"):
            counted[f"harden_{e['result']}"] += 1
        elif kind == "persistent_effect_added":
            counted["effect_added"] += 1
        elif kind == "persistent_effect_removed":
            counted[f"effect_removed_{e['reason']}"] += 1
        elif kind == "damage_prevented":
            counted["damage_prevented"] += 1
            counted[f"damage_prevented_by_{e['effect']}"] += 1
            prevented_in_attack = True
        elif kind == "special_condition" and prevented_in_attack:
            counted[f"effect_after_prevention_{e['condition']}"] += 1
        elif kind == "damage" and e.get("target") == "self" and prevented_in_attack:
            counted["self_damage_after_prevention"] += 1
        elif kind == "turn_end":
            prevented_in_attack = False
        elif kind == "knock_out" and "evolution_stack" in e:
            counted["knock_out_evolved"] += 1
            counted[f"knock_out_evolved_{state.cards[e['pokemon']].card_id}"] += 1
        elif kind == "knock_out":
            counted["knock_out_basic"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    if any(p.active is not None and p.active.persistent_effects for p in state.players):
        counted["ended_with_effect"] += 1
    return counted


class FullGameWithHardenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_counts(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("evolve_to_PMCG1-003", "evolve_to_PMCG1-009", "harden", "harden_heads", "harden_tails", "damage_prevented",
                    "effect_removed_expired", "knock_out_evolved", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        # 「おもて」の数だけ効果を与え、与えた効果はどれも、期限切れ・きぜつで消えたか、終わった対戦に残っている
        self.assertEqual(counted["harden_heads"], counted["effect_added"])
        self.assertEqual(counted["harden"], counted["harden_heads"] + counted["harden_tails"] + counted["harden_confusion_failed"])
        self.assertEqual(counted["effect_added"],
                         counted["effect_removed_expired"] + counted["effect_removed_knock_out"] + counted["ended_with_effect"])
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
                    self.assertEqual(prizes[player], min(knock_outs[player], 6))

    def test_effects_never_outlive_their_turn(self):
        """どの局でも、効果は与えた番の次の番（相手の番）の終わりまでに消えるか、その番に対戦が終わっている。同じ効果を二度
        消さない。「ダメージを受けない」ポケモンへのダメージのログ（``damage``）はない。"""
        for key, (state, _, _) in self.games.items():
            log = [dict(e) for e in state.log]
            added = {(e["pokemon_id"], e["turn"]): e for e in log if e["kind"] == "persistent_effect_added"}
            removed = Counter((e["pokemon_id"], e["created_turn"]) for e in log if e["kind"] == "persistent_effect_removed")
            for (pokemon_id, created), event in added.items():
                with self.subTest(key=key, pokemon_id=pokemon_id, created=created):
                    self.assertLessEqual(removed[(pokemon_id, created)], 1)
                    if removed[(pokemon_id, created)] == 0:
                        self.assertIn(state.phase, TERMINAL)
                        self.assertLessEqual(state.turn_number, event["active_turn"])
            for e in log:
                if e["kind"] == "persistent_effect_removed" and e["reason"] == "expired":
                    self.assertEqual(e["turn"], e["active_turn"], key)

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
        """持続する効果の付与・解除・ダメージの無効は乱数を使わない。対戦準備のあとの乱数はコインだけ。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)


class GoldenHardenGameTest(unittest.TestCase):
    """「かたまる」の効果でダメージが無効になる対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.4b）。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED, cure=GOLDEN_CURE)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        self.assertGreater(count_events(state)["damage_prevented"], 0)
        data = full(state)
        # v0.69・v0.97: 写しの元を上げた（7d3f4ca・73a1690）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.4c・v0.4d・v0.5・v0.6・v0.7・v0.8・v0.9・v0.10・v0.11・v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class RandomCommandsWithHardenTest(unittest.TestCase):
    """正しい手順・でたらめな操作・でたらめな進化・にげるを混ぜる（固定 seed）。拒否は状態も乱数も変えない。"""

    def test_random_commands(self):
        generator = test_weedle_games.RandomCommandsWithWeedleTest()
        counted = Counter()
        for seed in range(12):
            r = random.Random(seed)
            state = new_game(*decks(seed), seed)
            for _ in range(400):
                if state.phase in TERMINAL:
                    break
                roll = r.random()
                if roll < 0.5:
                    command = policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0, tried=())
                elif roll < 0.65:
                    uids = list(state.cards) + [-1]
                    ids = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0]
                    command = EvolvePokemon(r.choice([0, 1]), r.choice(uids), r.choice(ids))
                elif roll < 0.8 and state.phase is Phase.MAIN:
                    command = UseAttack(state.current_player, r.choice([0, 1, 2]))
                elif roll < 0.9 and state.phase is Phase.MAIN and state.players[state.current_player].bench:
                    p = state.players[state.current_player]
                    cost = state.card_def(p.active.card).retreat_cost
                    command = Retreat(state.current_player, tuple(p.active.energy[:cost]), r.choice(p.bench).card)
                else:
                    command = generator.random_command(r, state)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted[f"rejected_{error.code}"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                for e in new.log[len(state.log):]:
                    counted[e["kind"]] += 1
                state = new
        for key in ("persistent_effect_added", "persistent_effect_removed", "damage_prevented", "evolve"):
            self.assertGreater(counted[key], 0, (key, counted))


# 自然な対戦（CURE_SEEDS の 20 局・NO_CURE_SEEDS の 20 局）で数えた回数（v0.4b）。手順・デッキ・乱数の使い方が変わると変わる。
# 止まった 1 局は対戦準備の切り直しの補償（v0.1 からの未解決）。効果を与えた 195 回のうち、191 回は次の相手の番の終わりに
# 消え（expired）、1 回はポケモンチェックのどくできぜつして消え（knock_out）、3 回は効果のはたらく番に対戦が終わった
# （ended_with_effect）。ベンチに戻る・進化して消えることは、自然な対戦では起こらない（単体テストで確かめる）
EXPECTED_COUNTS = {
    "evolve": 239, "evolve_to_PMCG1-003": 125, "evolve_to_PMCG1-009": 114,
    "rejected_evolve_FIRST_TURN_EVOLUTION": 37, "rejected_evolve_PLAYED_THIS_TURN": 109,
    "harden": 392, "harden_heads": 195, "harden_tails": 184, "harden_confusion_failed": 13, "effect_added": 195,
    "effect_removed_expired": 191, "effect_removed_knock_out": 1, "ended_with_effect": 3,
    "damage_prevented": 103, "damage_prevented_by_PMCG1-002#0": 19, "damage_prevented_by_PMCG1-003#1": 14,
    "damage_prevented_by_PMCG1-004#0": 25, "damage_prevented_by_PMCG1-009#1": 6, "damage_prevented_by_PMCG1-015#0": 30,
    "damage_prevented_by_PMCG1-035#0": 6, "damage_prevented_by_PMCG1-035#1": 1, "damage_prevented_by_PMCG2-003#0": 2,
    "effect_after_prevention_confusion": 13, "effect_after_prevention_paralysis": 19, "effect_after_prevention_poison": 14,
    "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE": 13, "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 5,
    "rejected_attack_POKEMON_ASLEEP": 79, "rejected_attack_POKEMON_PARALYZED": 119, "rejected_retreat_POKEMON_ASLEEP": 85,
    "rejected_retreat_POKEMON_PARALYZED": 137, "rejected_retreat_RETREAT_ALREADY_FAILED": 9,
    "knock_out_evolved": 59, "knock_out_evolved_PMCG1-003": 33, "knock_out_evolved_PMCG1-009": 26, "knock_out_basic": 130,
    "take_prize": 189, "phase_game_over": 39, "phase_halted": 1, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 1,
}
# cure seed 2: 225 コマンド、88 番で勝敗が決まる（「かたまる」16 回・「おもて」12 回、ダメージの無効 9 回（どくばり 8・
# あやしいひかり 1）、無効のあとのどく 4 回）
GOLDEN_SEED = 2
GOLDEN_CURE = True
GOLDEN_SHAPE = (225, 88, Phase.GAME_OVER)
GOLDEN_DIGEST = "71f3be1cf00d48cf5655c035e89e53fc9968acddf42d28aefc96ca39b289b8e5"


if __name__ == "__main__":
    unittest.main()
