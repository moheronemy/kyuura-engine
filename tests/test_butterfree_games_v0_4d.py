"""バタフリー（v0.4d）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

キャタピー → トランセル → バタフリーの 2 進化と、「ふきとばし」（ワザの途中で相手が入れ替わる控えを選ぶ決定）・
「メガドレイン」（与えたダメージの半分の回復）を、v0.4c までのカード（ビードル → コクーン → スピアー・「かたまる」・
ロコン・パラス → パラセクト・ピカチュウ・ガーディ・プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすり）と
混ぜる。17.3 の出来事（バタフリーへの進化・ふきとばし・相手の選択・控えのいない相手・強制交代による特殊状態と持続する
効果の解除・メガドレイン・回復・回復 0・ダメージの防止・バタフリーのきぜつと 3 枚のトラッシュ・勝敗）が自然な対戦の中で
起こる回数を数えて固定する（docs/architecture-v0.4d.md 13 章）。根拠のページは tests/test_forced_switch_v0_4d.py・
tests/test_damage_drain_v0_4d.py・tests/test_butterfree_v0_4d.py（p.19・p.89・p.159・p.213・p.309・p.311・p.319〜p.323）。

手順は test_stage2_games_v0_4c.py の ``policy_command`` に、バタフリーのワザの選び方と「ふきとばし」の決定への答え方を
加えたもの（対戦相手の AI ではない）。
"""

import hashlib
import json
import random
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn, EngineError, EvolvePokemon, IllegalActionError, Phase, ResolveDecision, Retreat, UnsupportedError, UseAttack, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    driver_retreat_cost,
    BEEDRILL, BILL, BUTTERFREE, CATERPIE, DEFENDER, FIRE, GRASS, GROWLITHE, KAKUNA, LIGHTNING, METAPOD, PARAS, PARASECT,
    PIKACHU, PLUSPOWER, POTION, SWITCH, VULPIX, WEEDLE, coin_events, expand_decklist,
)
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS, policy_command as stage2_policy_command
from tests import test_weedle_games

BUTTERFREE_DECK_A = expand_decklist({
    CATERPIE: 4, METAPOD: 4, BUTTERFREE: 3, WEEDLE: 3, KAKUNA: 3, BEEDRILL: 2, PLUSPOWER: 2, DEFENDER: 2, SWITCH: 2, BILL: 3,
    POTION: 2, GRASS: 30,
})
BUTTERFREE_DECK_B = expand_decklist({
    CATERPIE: 4, METAPOD: 3, BUTTERFREE: 3, VULPIX: 3, PARAS: 3, PARASECT: 2, PIKACHU: 2, GROWLITHE: 2, DEFENDER: 2, BILL: 3,
    GRASS: 22, FIRE: 7, LIGHTNING: 4,
})
CURE_SEEDS = tuple(range(20))
NO_CURE_SEEDS = tuple(range(300, 320))


def full(state):
    return state_to_dict(state, format_version=8)


def decks(seed):
    return (BUTTERFREE_DECK_A, BUTTERFREE_DECK_B) if seed % 2 == 0 else (BUTTERFREE_DECK_B, BUTTERFREE_DECK_A)


def butterfree_attack(state):
    """バタフリーのワザの選び方: 相手の対戦ポケモンが特殊状態か持続する効果を受けているか、相手に控えがいない、または偶数番目の
    自分の番なら「ふきとばし」（払えるとき）。そうでなければ、自分にダメージがあれば「メガドレイン」（払えるとき）。払えるほうを使う。"""
    player = state.current_player
    active = state.players[player].active
    opponent = state.players[1 - player]
    whirlwind, drain = (can_pay_cost(a.cost, state.energy_types(active)) for a in state.card_def(active.card).attacks)
    target = opponent.active
    prefer_whirlwind = bool(target.conditions.names() or target.persistent_effects or not opponent.bench
                            or (state.turn_number // 2) % 2 == 0)
    if whirlwind and (prefer_whirlwind or not drain):
        return UseAttack(player, 0)
    if drain:
        return UseAttack(player, 1)
    return None


def retreat_to_butterfree(state, tried):
    """相手の対戦ポケモンが特殊状態か持続する効果を受けていて、ベンチに「ふきとばし」を払えるバタフリーがいれば、バトル場の
    ポケモンをにげさせてバタフリーを出す（にげるエネルギーを払えるとき。番ごとに一度だけ試す）。強制交代で特殊状態・持続する
    効果が消える場面を自然な対戦の中で起こすための手順。"""
    player = state.current_player
    p = state.players[player]
    target = state.players[1 - player].active
    if "retreat" in tried or not (target.conditions.names() or target.persistent_effects):
        return None
    if state.cards[p.active.card].card_id == BUTTERFREE:
        return None
    for pokemon in p.bench:
        if state.cards[pokemon.card].card_id != BUTTERFREE:
            continue
        if not can_pay_cost(state.card_def(pokemon.card).attacks[0].cost, state.energy_types(pokemon)):
            continue
        cost = driver_retreat_cost(state, p.active)
        if len(p.active.energy) < cost:
            return None
        return Retreat(player, tuple(p.active.energy[:cost]), pokemon.card)
    return None


def policy_command(state, *, janken_winner, cure, tried):
    """v0.4c の手順（1 進化・2 進化・「かたまる」・スピアー）に、バタフリーのワザと「ふきとばし」の決定への答えを加える。
    「ふきとばし」で入れ替わる控えは、相手が番ごとに違う位置を選ぶ（選べるもののうち、番の番号で決まる位置）。ワザを使う前に、
    ``retreat_to_butterfree`` の条件に合えばバタフリーに入れ替える。"""
    if state.phase is Phase.DECISION and state.decision.kind == FORCED_SWITCH:
        d = state.decision
        return ResolveDecision(d.player, d.id, (d.options[state.turn_number % len(d.options)],))
    command = stage2_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)):
        return command
    retreat = retreat_to_butterfree(state, tried)
    if retreat is not None:
        return retreat
    if isinstance(command, UseAttack) and state.cards[state.players[state.current_player].active.card].card_id == BUTTERFREE:
        return butterfree_attack(state) or command
    return command


def play_game(seed, *, cure=True, max_steps=8000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・相手の選択などの観測を返す。"""
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
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        if state.phase is Phase.DECISION and state.decision.kind == FORCED_SWITCH:
            # 相手の選択: 決定するのはワザを使われた側で、番のプレイヤーはワザを使った側のまま（5.2）
            assert state.decision.player != state.current_player and command.player == state.decision.player
            observed["forced_switch_chosen_by_opponent"] += 1
            observed[f"forced_switch_options_{len(state.decision.options)}"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。バタフリーのワザはワザを使ったポケモンのカードで見分ける。"""
    counted = Counter()
    last_attack = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            last_attack = (state.cards[e["pokemon"]].card_id, e["attack"])
            if last_attack[0] == BUTTERFREE:
                counted[f"butterfree_{e['attack']}"] += 1
        elif kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "confusion_check" and e["action"] == "attack" and not e["succeeded"] and last_attack and last_attack[0] == BUTTERFREE:
            counted["butterfree_confusion_failed"] += 1
        elif kind == "damage" and last_attack == (BUTTERFREE, "メガドレイン") and e["amount"] == 0:
            counted["drain_no_damage"] += 1  # 最終ダメージ 0（与えなかった）: 回復しない
        elif kind == "forced_switch":
            counted["forced_switch"] += 1
        elif kind == "forced_switch_skipped":
            counted[f"forced_switch_skipped_{e['reason']}"] += 1
        elif kind == "special_conditions_removed" and e["reason"] == "forced_switch":
            counted["forced_switch_cleared_conditions"] += 1
        elif kind == "persistent_effect_removed" and e["reason"] == "forced_switch":
            counted["forced_switch_removed_persistent_effect"] += 1
        elif kind == "drain_heal":
            counted["drain_heal" if e["counters"] else "drain_heal_zero"] += 1
            counted["drain_heal_counters"] += e["counters"]
        elif kind == "damage_prevented":
            counted["damage_prevented"] += 1
            if e["effect"].startswith(BUTTERFREE):
                counted[f"damage_prevented_by_{e['effect']}"] += 1
        elif kind == "knock_out":
            stack = e.get("evolution_stack", ())
            if state.cards[e["pokemon"]].card_id == BUTTERFREE:
                counted[f"knock_out_butterfree_{e.get('timing', 'attack')}"] += 1
                if all(uid in state.players[e["player"]].discard for uid in (*stack, e["pokemon"])):
                    counted["knock_out_butterfree_three_cards_in_discard"] += 1
            counted[f"knock_out_{len(stack) + 1}_cards"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithButterfreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {("cure", seed): play_game(seed) for seed in CURE_SEEDS}
        cls.games.update({("no_cure", seed): play_game(seed, cure=False) for seed in NO_CURE_SEEDS})

    def test_counts(self):
        """17.3 の出来事が、自然な対戦の中で実際に起こる（バタフリーのワザが 1 回も使われない試験を成功と数えない）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        for key in ("evolve_to_PMCG2-007", "butterfree_ふきとばし", "butterfree_メガドレイン", "forced_switch_chosen_by_opponent",
                    "forced_switch", "forced_switch_skipped_no_bench", "forced_switch_cleared_conditions", "drain_heal",
                    "drain_heal_zero", "knock_out_butterfree_attack", "knock_out_butterfree_three_cards_in_discard", "take_prize",
                    "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        # 相手が選んだ回数 = 入れ替えた回数（選んだら必ず入れ替える。二重にはしない）
        self.assertEqual(counted["forced_switch_chosen_by_opponent"], counted["forced_switch"])
        # こんらんで失敗しなかったバタフリーのワザは、ちょうど 1 つの結果になる: ふきとばしは入れ替える・入れ替えない（控えなし・
        # きぜつ）、メガドレインは回復する（0 個を含む）・ダメージを与えなかった（防いだ・最終ダメージ 0）
        self.assertEqual(counted["butterfree_ふきとばし"] + counted["butterfree_メガドレイン"] - counted["butterfree_confusion_failed"],
                         counted["forced_switch"] + counted["forced_switch_skipped_no_bench"]
                         + counted["forced_switch_skipped_knocked_out"] + counted["drain_heal"] + counted["drain_heal_zero"]
                         + counted["damage_prevented_by_PMCG2-007#1"] + counted["drain_no_damage"])
        self.assertEqual(counted["knock_out_butterfree_attack"] + counted["knock_out_butterfree_pokemon_check"],
                         counted["knock_out_butterfree_three_cards_in_discard"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_and_prizes(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertEqual(check_invariants(state), [])
                log = [dict(e) for e in state.log]
                knock_outs = Counter(1 - e["player"] for e in log if e["kind"] == "knock_out")
                prizes = Counter(e["player"] for e in log if e["kind"] == "take_prize")
                for player in (0, 1):
                    self.assertEqual(prizes[player], min(knock_outs[player], 6))
                for e in log:
                    if e["kind"] == "knock_out" and state.cards[e["pokemon"]].card_id == BUTTERFREE:
                        self.assertEqual([state.cards[u].card_id for u in e["evolution_stack"]], [CATERPIE, METAPOD])

    def test_games_end_and_replay(self):
        for key, (state, _, _) in self.games.items():
            with self.subTest(key=key):
                self.assertIn(state.phase, TERMINAL)
        for key in (("cure", 0), ("cure", 3), ("no_cure", 301)):
            state, commands, _ = self.games[key]
            replayed = new_game(*decks(key[1]), key[1])
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))

    def test_only_coins_use_randomness_after_setup(self):
        """ふきとばし・メガドレイン・相手の選択・強制交代は乱数を使わない。対戦準備のあとの乱数はコインだけ。"""
        for key, (state, _, _) in self.games.items():
            expected = copy_rng(new_game(*decks(key[1]), key[1]).rng)
            for event in coin_events(state):
                self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected), key)

    def test_each_decision_is_answered_once(self):
        """どの「ふきとばし」の決定も、相手の答え 1 回で閉じ、その番のワザのログ・番の終わり・ポケモンチェックは 1 回ずつ。"""
        for key, (state, _, _) in self.games.items():
            per_turn = Counter((e["turn"], e["kind"]) for e in state.log if e["kind"] in ("attack", "turn_end", "pokemon_check", "forced_switch"))
            for (turn, kind), count in per_turn.items():
                with self.subTest(key=key, turn=turn, kind=kind):
                    self.assertEqual(count, 1)


class GoldenButterfreeGameTest(unittest.TestCase):
    """バタフリーに 2 進化し、ふきとばし・メガドレインを使う対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.4d）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_CURE)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evolve_to_PMCG2-007", "butterfree_ふきとばし", "butterfree_メガドレイン", "forced_switch"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertGreater(observed["forced_switch_chosen_by_opponent"], 0)
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.5・v0.6・v0.7・v0.8・v0.9・v0.10・v0.11・v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class RandomCommandsWithButterfreeTest(unittest.TestCase):
    """正しい手順・でたらめな操作・でたらめな決定への答え（ワザを使った側・ない番号・古い番号）・進化・ワザ・にげるを混ぜる
    （固定 seed）。拒否は状態も乱数もログも変えない。相手の決定を待つ間に受け付けるのは、相手の正しい答えだけ。"""

    def test_random_commands(self):
        generator = test_weedle_games.RandomCommandsWithWeedleTest()
        counted = Counter()
        for seed in range(16):
            r = random.Random(seed)
            state = new_game(*decks(seed), seed)
            for _ in range(600):
                if state.phase in TERMINAL:
                    break
                roll = r.random()
                if state.phase is Phase.DECISION and state.decision.kind == FORCED_SWITCH and roll < 0.7:
                    # でたらめな答え: 答えるプレイヤー・決定の番号・選ぶもの（場のどのポケモン・ない番号・全部・空・重複）のどれかを崩す
                    d = state.decision
                    in_play = [pk.pokemon_id for p in state.players for pk in p.in_play()] + [0, 999]
                    player, decision, choices = d.player, d.id, (r.choice(d.options),)
                    broken = r.choice(["none", "player", "id", "choice", "choice", "count"])
                    if broken == "player":
                        player = r.choice([1 - d.player, 2, -1])
                    elif broken == "id":
                        decision = r.choice([d.id - 1, d.id + 1, 0])
                    elif broken == "choice":
                        choices = (r.choice(in_play),)
                    elif broken == "count":
                        choices = r.choice([(), tuple(d.options) + (d.options[0],), (d.options[0], d.options[0])])
                    command = ResolveDecision(player, decision, choices)
                elif roll < 0.5:
                    command = policy_command(state, janken_winner=seed % 2, cure=seed % 3 != 0, tried=())
                elif roll < 0.65:
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
                waiting = state.decision if state.phase is Phase.DECISION else None
                try:
                    new = apply_command(state, command)
                except EngineError as error:
                    counted[f"rejected_{error.code}"] += 1
                    if waiting is not None and waiting.kind == FORCED_SWITCH:
                        counted["rejected_while_waiting_forced_switch"] += 1
                    self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                    self.assertIs(state.log, log)
                    continue
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint), command)
                if waiting is not None and waiting.kind == FORCED_SWITCH:
                    # 受け付けたのは、相手（決定するプレイヤー）の、今の決定の番号での、選べるもの 1 つの答えだけ
                    self.assertIsInstance(command, ResolveDecision)
                    self.assertEqual((command.player, command.decision, len(command.choices)), (waiting.player, waiting.id, 1))
                    self.assertIn(command.choices[0], waiting.options)
                    counted["accepted_forced_switch_answer"] += 1
                for e in new.log[len(state.log):]:
                    counted[e["kind"]] += 1
                state = new
        for key in ("forced_switch", "accepted_forced_switch_answer", "rejected_while_waiting_forced_switch", "rejected_NOT_YOUR_DECISION",
                    "rejected_WRONG_DECISION", "rejected_INVALID_CHOICE", "rejected_INVALID_CHOICE_COUNT", "drain_heal"):
            self.assertGreater(counted[key], 0, (key, counted))


# 自然な対戦（CURE_SEEDS の 20 局・NO_CURE_SEEDS の 20 局）で数えた回数（v0.4d）。手順・デッキ・乱数の使い方が変わると変わる。
# 止まった 3 局は対戦準備の切り直しの補償（v0.1 からの未解決）。バタフリーへの進化 72 回、ふきとばし 133 回（こんらんで失敗 2 回）:
# 相手が選んで入れ替えた 82 回（控え 1 匹 25・2 匹 17・3 匹 17・4 匹 4・5 匹 19。特殊状態を消した 4 回・持続する効果を消した 6 回・
# ダメージを防がれたまま入れ替えた 6 回）、控えがいないので入れ替えない 11 回、20 ダメージできぜつしたので入れ替えない 38 回。
# メガドレイン 39 回: 回復 32 回（合計 62 個）・のっているカウンターがなく 0 個 7 回。バタフリーのきぜつ 20 回（ワザのあと 18・
# ポケモンチェックのどく 2）はどれも 3 枚をトラッシュした。「かたまる」の相手へのメガドレイン・最終ダメージ 0 のメガドレインは
# 自然な対戦では起こらなかった（tests/test_damage_drain_v0_4d.py で盤面を直接作って確かめた）
EXPECTED_COUNTS = {
    "butterfree_confusion_failed": 2, "butterfree_ふきとばし": 133, "butterfree_メガドレイン": 39, "damage_prevented": 18,
    "damage_prevented_by_PMCG2-007#0": 6, "drain_heal": 32, "drain_heal_counters": 62, "drain_heal_zero": 7, "evolve_to_PMCG1-003": 94,
    "evolve_to_PMCG1-009": 38, "evolve_to_PMCG1-012": 28, "evolve_to_PMCG2-007": 72, "evolve_to_PMCG2-010": 25, "forced_switch": 82,
    "forced_switch_chosen_by_opponent": 82, "forced_switch_cleared_conditions": 4, "forced_switch_options_1": 25,
    "forced_switch_options_2": 17, "forced_switch_options_3": 17, "forced_switch_options_4": 4, "forced_switch_options_5": 19,
    "forced_switch_removed_persistent_effect": 6, "forced_switch_skipped_knocked_out": 38, "forced_switch_skipped_no_bench": 11,
    "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "knock_out_1_cards": 150, "knock_out_2_cards": 14, "knock_out_3_cards": 27,
    "knock_out_butterfree_attack": 18, "knock_out_butterfree_pokemon_check": 2, "knock_out_butterfree_three_cards_in_discard": 20,
    "phase_game_over": 37, "phase_halted": 3, "rejected_attack_POKEMON_ASLEEP": 30, "rejected_attack_POKEMON_PARALYZED": 80,
    "rejected_evolve2_EVOLVED_THIS_TURN": 50, "rejected_evolve_FIRST_TURN_EVOLUTION": 24, "rejected_evolve_PLAYED_THIS_TURN": 65,
    "rejected_retreat_POKEMON_ASLEEP": 33, "rejected_retreat_POKEMON_PARALYZED": 116, "rejected_retreat_RETREAT_ALREADY_FAILED": 3,
    "take_prize": 191,
}
# cure seed 0: 125 コマンド、39 番で勝敗が決まる（バタフリーへの進化 2 回、ふきとばし 2 回（相手が 2 匹の控えから選んだ）、
# メガドレイン 2 回（4 個の回復）、バタフリーのきぜつ 1 回）
GOLDEN_SEED = 0
GOLDEN_CURE = True
GOLDEN_SHAPE = (125, 39, Phase.GAME_OVER)
GOLDEN_DIGEST = "dbf3f07327b1e853799f6796dc8183324ed148d194ada4c89f8637550966db7c"


if __name__ == "__main__":
    unittest.main()
