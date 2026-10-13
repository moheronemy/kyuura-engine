"""2 進化（v0.4c）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ビードル → コクーン → スピアーの 2 進化を、v0.4b までのカード（キャタピー → トランセル・「かたまる」・パラス → パラセクト・
ロコン・ピカチュウ・ガーディ・ドードー・プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすり）と混ぜる。
1 進化・2 進化の成功、同じ番の再進化の拒否（``EVOLVED_THIS_TURN``）、バトル場・ベンチでの 2 進化、ダブルニードル・
どくばりの使用、どくの付与、「かたまる」の相手へのダブルニードルの拒否（``UNRESOLVED_PREVENTED_COIN_DAMAGE``）、
2 進化ポケモンのきぜつ（3 枚のトラッシュ）・サイドが、自然な対戦の中で起こる回数を数えて固定する
（docs/stage2-state-v0.4c.md 12 章）。根拠のページは tests/test_stage2_v0_4c.py（p.309・p.310・p.313・p.316・p.319・
p.322〜324・p.21）。

手順は test_harden_games_v0_4b.py の ``policy_command`` に、2 進化（``stage2_command``）とスピアーのワザの選び方を加えた
もの（対戦相手の AI ではない）。1 進化したポケモンを同じ番に 2 進化させる操作を、番ごとに一度だけ試す（拒否されることを
確かめる）。
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
    BEEDRILL, BILL, CATERPIE, DEFENDER, DODUO, FIRE, GRASS, GROWLITHE, KAKUNA, LIGHTNING, METAPOD, PARAS, PARASECT, PIKACHU,
    PLUSPOWER, POTION, SWITCH, VULPIX, WEEDLE, coin_events, expand_decklist,
)
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS, policy_command as harden_policy_command
from tests import test_weedle_games

STAGE2_DECK_A = expand_decklist({
    WEEDLE: 4, KAKUNA: 4, BEEDRILL: 3, CATERPIE: 3, METAPOD: 3, DODUO: 2, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2, BILL: 3,
    POTION: 2, GRASS: 30,
})
STAGE2_DECK_B = expand_decklist({
    WEEDLE: 4, KAKUNA: 3, BEEDRILL: 3, VULPIX: 3, PARAS: 3, PARASECT: 2, PIKACHU: 2, GROWLITHE: 2, DEFENDER: 2, SWITCH: 2,
    BILL: 3, GRASS: 20, FIRE: 7, LIGHTNING: 4,
})
CURE_SEEDS = tuple(range(20))
NO_CURE_SEEDS = tuple(range(300, 320))
# 2 進化の拒否として数えるコード（自然な対戦の手順で起こるのは、同じ番に 1 進化したポケモンへの 2 進化だけ）
STAGE2_REJECTIONS = ("EVOLVED_THIS_TURN",)


def full(state):
    return state_to_dict(state, format_version=8)


def decks(seed):
    return (STAGE2_DECK_A, STAGE2_DECK_B) if seed % 2 == 0 else (STAGE2_DECK_B, STAGE2_DECK_A)


def stage2_command(state, *, tried=()):
    """手札の 2 進化カードを、名前の合う自分の場の 1 進化ポケモンに重ねる（バトル場から先）。進化できるポケモンがいなければ、
    名前の合うポケモン（この番に 1 進化したもの）に一度だけ試す（``EVOLVED_THIS_TURN`` で拒否されることを確かめる）。"""
    player = state.current_player
    p = state.players[player]
    eligible, ineligible = [], []
    for uid in p.hand:
        definition = state.card_def(uid)
        if not definition.is_stage2_pokemon:
            continue
        for target in p.in_play():
            if state.card_def(target.card).name_ja != definition.evolves_from:
                continue
            ok = target.current_form_turn < state.turn_number
            (eligible if ok else ineligible).append(EvolvePokemon(player, uid, target.pokemon_id))
    if eligible:
        return eligible[0]
    if ineligible and "evolve2" not in tried:
        return ineligible[0]
    return None


def policy_command(state, *, janken_winner, cure, tried):
    """v0.4b の手順（1 進化・「かたまる」を含む）のあと、2 進化を試し、スピアーのワザを選ぶ: 相手の対戦ポケモンがどく状態で
    なく、どくばり（草 3）を払えて、偶数番目の自分の番ならどくばり、そうでなければダブルニードル（無色 3）を払えるなら
    ダブルニードル、払えなければどくばり。"""
    command = harden_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)):
        return command
    evolve = stage2_command(state, tried=tried)
    if evolve is not None:
        return evolve
    if isinstance(command, UseAttack):
        player = state.current_player
        active = state.players[player].active
        if state.cards[active.card].card_id == BEEDRILL:
            provided = state.energy_types(active)
            twineedle, sting = (can_pay_cost(a.cost, provided) for a in state.card_def(active.card).attacks)
            opponent = state.players[1 - player].active
            if sting and opponent.conditions.poison is None and (state.turn_number // 2) % 2 == 0:
                return UseAttack(player, 1)
            if twineedle:
                return UseAttack(player, 0)
            if sting:
                return UseAttack(player, 1)
    return command


def play_game(seed, *, cure=True, max_steps=8000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・2 進化の場所の観測を返す。"""
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
                if isinstance(command, EvolvePokemon):
                    stage2 = state.card_def(command.card).is_stage2_pokemon
                    if error.code in (STAGE2_REJECTIONS if stage2 else EVOLUTION_REJECTIONS):
                        observed[f"rejected_{'evolve2' if stage2 else 'evolve'}_{error.code}"] += 1
                        turn_tried.add("evolve2" if stage2 else "evolve")
                        continue
                if error.code not in REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                if error.code == "UNRESOLVED_PREVENTED_COIN_DAMAGE":
                    observed[f"rejected_attack_by_{state.cards[state.players[command.player].active.card].card_id}"] += 1
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        if isinstance(command, EvolvePokemon) and state.card_def(command.card).is_stage2_pokemon:
            where = "active" if state.players[command.player].active.pokemon_id == command.target else "bench"
            observed[f"evolve2_{where}"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。スピアーのワザは、ワザを使ったポケモンのカードで見分ける（ビードルにも「どくばり」がある）。"""
    counted = Counter()
    last_attack = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            last_attack = (state.cards[e["pokemon"]].card_id, e["attack"])
        if kind == "evolve":
            counted["evolve"] += 1
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attack" and state.cards[e["pokemon"]].card_id == BEEDRILL:
            counted[f"beedrill_{e['attack']}"] += 1
        elif kind == "confusion_check" and e["action"] == "attack" and not e["succeeded"] and last_attack == (BEEDRILL, "ダブルニードル"):
            counted["twineedle_confusion_failed"] += 1  # こんらんのコインが「うら」: ダブルニードルのコインは投げない（p.309 の手順 5）
        elif kind == "coin_flip" and e["source"] == "attack" and e["effect"] == f"{BEEDRILL}#0":
            counted[f"twineedle_coin_{e['result']}"] += 1
        elif kind == "coin_flip" and e["source"] == "attack" and e["effect"] == f"{BEEDRILL}#1":
            counted[f"poison_sting_coin_{e['result']}"] += 1
        elif kind == "special_condition" and e.get("effect") == f"{BEEDRILL}#1":
            counted[f"beedrill_{'already' if e.get('already') else 'gave'}_{e['condition']}"] += 1
        elif kind == "damage_prevented":
            counted["damage_prevented"] += 1
            if e["effect"] == f"{BEEDRILL}#1":
                counted["damage_prevented_by_beedrill"] += 1
        elif kind == "knock_out":
            stack = e.get("evolution_stack", ())
            counted[f"knock_out_{len(stack) + 1}_cards"] += 1
            if len(stack) == 2:
                counted[f"knock_out_stage2_{e.get('timing', 'attack')}"] += 1
                if all(uid in state.players[e["player"]].discard for uid in (*stack, e["pokemon"])):
                    counted["knock_out_stage2_three_cards_in_discard"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithStage2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_counts(self):
        """21.1・21.3 の出来事が、自然な対戦の中で実際に起こる（2 進化が 1 回も起こらない試験を成功と数えない）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("evolve_to_PMCG1-009", "evolve_to_PMCG1-012", "rejected_evolve2_EVOLVED_THIS_TURN", "evolve2_active",
                    "evolve2_bench", "beedrill_ダブルニードル", "beedrill_どくばり", "beedrill_gave_poison", "knock_out_3_cards",
                    "knock_out_stage2_attack", "knock_out_stage2_three_cards_in_discard", "take_prize", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["evolve_to_PMCG1-012"], counted["evolve2_active"] + counted["evolve2_bench"])
        self.assertEqual(counted["knock_out_3_cards"], counted["knock_out_stage2_three_cards_in_discard"])
        self.assertEqual(counted["twineedle_coin_heads"] + counted["twineedle_coin_tails"], 2 * counted["beedrill_ダブルニードル"]
                         - 2 * counted["twineedle_confusion_failed"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_stack_shapes_and_prizes(self):
        """どの局も、終わった状態で不変条件を満たし、取ったサイドの数ときぜつの数が合う（3 枚の 2 進化ポケモンも 1 匹で 1 枚）。
        きぜつのログの重なりは下から たねポケモン・1 進化・2 進化の順。"""
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertEqual(check_invariants(state), [])
                log = [dict(e) for e in state.log]
                knock_outs = Counter(1 - e["player"] for e in log if e["kind"] == "knock_out")
                prizes = Counter(e["player"] for e in log if e["kind"] == "take_prize")
                for player in (0, 1):
                    self.assertEqual(prizes[player], min(knock_outs[player], 6))
                for e in log:
                    if e["kind"] == "knock_out" and len(e.get("evolution_stack", ())) == 2:
                        ids = [state.cards[u].card_id for u in (*e["evolution_stack"], e["pokemon"])]
                        self.assertEqual(ids, [WEEDLE, KAKUNA, BEEDRILL])

    def test_evolutions_happen_on_different_turns(self):
        """どの 2 進化ポケモンも、1 進化と 2 進化は別の番（持ち主の番、3 番以降）。同じ番に二度進化したログはない。"""
        for key, (state, _, _) in self.games.items():
            by_pokemon = {}
            for e in state.log:
                if e["kind"] == "evolve":
                    by_pokemon.setdefault(e["pokemon_id"], []).append(e)
            for pokemon_id, events in by_pokemon.items():
                with self.subTest(key=key, pokemon_id=pokemon_id):
                    turns = [e["turn"] for e in events]
                    self.assertEqual(turns, sorted(set(turns)))
                    self.assertTrue(all(turn >= 3 for turn in turns))
                    if len(events) == 2:
                        self.assertEqual([e["to_card_id"] for e in events], [KAKUNA, BEEDRILL])

    def test_games_end_and_replay(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertIn(state.phase, (Phase.GAME_OVER, Phase.SUDDEN_DEATH, Phase.HALTED))
        for key in (("cure", 0), ("cure", 3), ("no_cure", 301)):
            state, commands, _ = self.games[key]
            replayed = new_game(*decks(key[1]), key[1])
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))

    def test_only_coins_use_randomness_after_setup(self):
        """2 進化・きぜつ・3 枚のトラッシュは乱数を使わない。対戦準備のあとの乱数はコイン（ダブルニードルは 1 枚 1 回で 2 回）だけ。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)

    def test_log_must_cover_every_evolution(self):
        """``new_game`` から始めた対戦はログが最初からあるので、2 進化ポケモンの 2 回の進化のどちらのログが欠けても、
        不変条件で見つかる（v0.4c。テスト専用に作った盤面には求めない）。"""
        for key, (state, commands, _) in self.games.items():
            for index in range(len(commands)):
                partial = new_game(*decks(key[1]), key[1])
                for command in commands[:index]:
                    partial = apply_command(partial, command)
                stage2 = [pk for p in partial.players for pk in p.in_play() if len(pk.evolution_stack) == 2]
                if stage2:
                    break
            else:
                continue
            target = stage2[0]
            for drop in (0, 1):
                with self.subTest(key=key, drop=drop):
                    broken = partial.clone()
                    events = [e for e in broken.log if e["kind"] == "evolve" and e["pokemon_id"] == target.pokemon_id]
                    broken.log = tuple(e for e in broken.log if e is not events[drop])
                    self.assertTrue(any("進化のログが 1 回" in p for p in check_invariants(broken)), check_invariants(broken))
            return
        self.fail("2 進化したポケモンのいる局面が見つからない")


class GoldenStage2GameTest(unittest.TestCase):
    """2 進化したスピアーがワザを使い、きぜつする対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.4c）。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED, cure=GOLDEN_CURE)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evolve_to_PMCG1-012", "beedrill_ダブルニードル", "knock_out_3_cards"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.9")  # v0.4d・v0.5・v0.6・v0.7・v0.8 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class RandomCommandsWithStage2Test(unittest.TestCase):
    """正しい手順・でたらめな操作・でたらめな進化（2 進化を含む）・ワザ・にげるを混ぜる（固定 seed）。拒否は状態も乱数も
    ログも変えない。"""

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
                    # 手札の進化カード（1 進化・2 進化）を、でたらめな場のポケモンに重ねることを多めに試す
                    player = state.current_player if state.current_player in (0, 1) and r.random() < 0.8 else r.choice([0, 1])
                    in_hand = [u for u in state.players[player].hand if state.card_def(u).is_evolution_pokemon]
                    uids = (in_hand if in_hand and r.random() < 0.7 else list(state.cards)) + [-1]
                    ids = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0]
                    command = EvolvePokemon(player, r.choice(uids), r.choice(ids))
                elif roll < 0.8 and state.phase is Phase.MAIN:
                    command = UseAttack(state.current_player, r.choice([0, 1, 2]))
                elif roll < 0.9 and state.phase is Phase.MAIN and state.players[state.current_player].bench:
                    p = state.players[state.current_player]
                    cost = state.card_def(p.active.card).retreat_cost
                    command = Retreat(state.current_player, tuple(p.active.energy[:cost]), r.choice(p.bench).card)
                else:
                    command = generator.random_command(r, state)
                before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted[f"rejected_{error.code}"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    self.assertIs(state.log, log)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                for e in new.log[len(state.log):]:
                    counted[e["kind"]] += 1
                    if e["kind"] == "evolve":
                        counted[f"evolve_to_{e['to_card_id']}"] += 1
                state = new
        for key in ("evolve_to_PMCG1-012", "rejected_EVOLVED_THIS_TURN", "rejected_EVOLUTION_NAME_MISMATCH", "knock_out"):
            self.assertGreater(counted[key], 0, (key, counted))


# 自然な対戦（CURE_SEEDS の 20 局・NO_CURE_SEEDS の 20 局）で数えた回数（v0.4c）。手順・デッキ・乱数の使い方が変わると変わる。
# 止まった 3 局は対戦準備の切り直しの補償（v0.1 からの未解決）。2 進化 79 回（バトル場 31・ベンチ 48）、同じ番の再進化の
# 拒否 51 回。スピアーのきぜつ 24 回はどれも 3 枚をトラッシュした（ワザのあと 14・ポケモンチェックのどく 10）。「かたまる」の
# 相手へのダブルニードルは 5 回とも UNRESOLVED_PREVENTED_COIN_DAMAGE で拒否され、どくばりは 2 回ダメージが無効になった
EXPECTED_COUNTS = {
    "beedrill_gave_poison": 14, "beedrill_どくばり": 55, "beedrill_ダブルニードル": 71, "damage_prevented": 21,
    "damage_prevented_by_beedrill": 2, "evolve": 243, "evolve2_active": 31, "evolve2_bench": 48, "evolve_to_PMCG1-003": 38,
    "evolve_to_PMCG1-009": 99, "evolve_to_PMCG1-012": 79, "evolve_to_PMCG2-010": 27,
    "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "knock_out_1_cards": 158, "knock_out_2_cards": 24, "knock_out_3_cards": 24,
    "knock_out_stage2_attack": 14, "knock_out_stage2_pokemon_check": 10, "knock_out_stage2_three_cards_in_discard": 24,
    "phase_game_over": 37, "phase_halted": 3, "poison_sting_coin_heads": 14, "poison_sting_coin_tails": 9,
    "rejected_attack_POKEMON_ASLEEP": 31, "rejected_attack_POKEMON_PARALYZED": 39,
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 1, "rejected_attack_UNRESOLVED_PREVENTED_COIN_DAMAGE": 5,
    "rejected_attack_by_PMCG1-012": 5, "rejected_evolve2_EVOLVED_THIS_TURN": 51, "rejected_evolve_FIRST_TURN_EVOLUTION": 26,
    "rejected_evolve_PLAYED_THIS_TURN": 73, "rejected_retreat_POKEMON_ASLEEP": 33, "rejected_retreat_POKEMON_PARALYZED": 78,
    "take_prize": 206, "twineedle_coin_heads": 64, "twineedle_coin_tails": 78,
}
# cure seed 2: 161 コマンド、51 番で勝敗が決まる（2 進化 3 回、ダブルニードル 8 回（コイン 16 枚）、どくばり 3 回、
# スピアーのきぜつ 2 回）
GOLDEN_SEED = 2
GOLDEN_CURE = True
GOLDEN_SHAPE = (161, 51, Phase.GAME_OVER)
GOLDEN_DIGEST = "53e6a10881f38a1fc1572977e6dd5d160b7bdbb6b158d7e7409db2ade3872d8e"


if __name__ == "__main__":
    unittest.main()
