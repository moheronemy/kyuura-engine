"""化石の秘密のゴース → ゴースト（v0.9）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ゴーストのポケモンパワー「とうめい」（ワザによってダメージや効果を受けるときに自動的にはたらき、コインが「おもて」なら、そのダメージと
効果を受けない。ねむり・マヒ・こんらんのとき、この力は消える）が、自然な対戦の中で、いろいろなワザ（ダメージだけ・ダメージとどく・
ふきとばし・メガドレイン・やどりぎのタネ・キノコのほうし・どくガス・ねばりつく・みだれづき・でんげき・あくむ・抵抗力で 0 になるワザ）を
受けるときにはたらくこと、かがくへんかガス（v0.8）と特殊状態で消えること、原典で決められない場合（T19b）で止まることを確かめる。

- 一方のデッキは、ゴース・ゴーストと、コラッタ・ドードー・ロケット団のベトベター・ベトベトン（自分のかがくへんかガスが、自分の
  ゴーストの「とうめい」も消す）。
- もう一方のデッキは、ゴーストに使うワザの種類を多くした（フシギソウ・バタフリー・パラス・ピカチュウ・ワンリキー・ベトベトン・
  ゴースト・キャタピー（いとをはく。T19b で止まる））。

自然な対戦の中で起こる出来事の回数を数えて固定する（docs/v0.9-verification.md 4 章）。盤面を直接作ったテスト
（tests/test_transparency_v0_9.py）とは別に数える。根拠のページは tests/test_transparency_v0_9.py（p.159・p.160・p.309・p.320・
p.321・p.323）・tests/test_haunter_line_v0_9.py（p.158・p.160）。手順は tests/test_muk_games_v0_8.py の ``policy_command`` に、次を
加えたもの（対戦相手の AI ではない）:

- エナジーへんかんの決定は、番の番号が 9 の倍数なら 1 枚、そうでなければ選べるだけ（2 枚まで）を、トラッシュの順に選ぶ（0 枚は選ばない。
  H4 は止める）。
- ゴースのワザ: トラッシュにエネルギーカードがあり、番の番号が 3 の倍数ならエナジーへんかん、そうでなければしたでなめる。
- ワザが ``UNRESOLVED_EVADED_EFFECT_COIN``（T19b）で止まったら、その番はほかの使えるワザ（止まらないもの）を 1 度だけ試し、
  なければ番を終える。
- 番の番号が 5 の倍数の番は、自分の場にゴーストがいれば一度だけ、「とうめい」の使用を試す（宣言しない特殊能力。``POWER_NOT_DECLARABLE``）。

「とうめい」がはたらいているかは、エンジンの関数を使わずに場から求める（``working``。ゴースト（いちばん上のカード）が、ねむり・マヒ・
こんらんでなく、場のベトベトン（いちばん上のカード）のうち、ねむり・マヒ・こんらんでないものがいない）。ワザを受け付けるたびに、
判定（evade_check）があればそのゴーストは ``working``、コインはゴースト側のプレイヤー、を確かめる。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.decisions import RECOVER_ENERGY
from kyuura_engine.effects import ConfuseOnHeads, ParalyzeOnHeads, PoisonOnHeads
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    BILL, BULBASAUR, BUTTERFREE, CATERPIE, DEFENDER, DODUO, FIGHTING, FIRE, GASTLY, GRASS, GRIMER, HAUNTER, IVYSAUR, LIGHTNING, MACHOP,
    METAPOD, MUK, PARAS, PIKACHU, PLUSPOWER, POTION, PSYCHIC, RATTATA, SWITCH, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_muk_games_v0_8 import policy_command as muk_policy_command
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# ゴース・ゴーストと、コラッタ・ドードー・ロケット団のベトベター・ベトベトン
HAUNTER_DECK_A = expand_decklist({
    GASTLY: 4, HAUNTER: 3, RATTATA: 4, DODUO: 2, GRIMER: 2, MUK: 1, BILL: 4, SWITCH: 2, POTION: 2, DEFENDER: 2, PSYCHIC: 22, GRASS: 8,
    FIRE: 4,
})
# ゴーストに使うワザの種類を多くしたデッキ（少しのゴースト・ベトベトン）
HAUNTER_DECK_B = expand_decklist({
    BULBASAUR: 3, IVYSAUR: 2, CATERPIE: 2, METAPOD: 1, BUTTERFREE: 2, PARAS: 2, PIKACHU: 2, MACHOP: 2, GRIMER: 2, MUK: 1, GASTLY: 2,
    HAUNTER: 1, PLUSPOWER: 2, BILL: 4, GRASS: 21, LIGHTNING: 3, FIGHTING: 3, PSYCHIC: 5,
})
SEEDS = tuple(range(80))
DECLARE_EVERY = 5  # 手順の決まりごと（ルールの制限ではない）
EVADED_COIN = "UNRESOLVED_EVADED_EFFECT_COIN"
EFFECT_COIN_TYPES = (PoisonOnHeads, ParalyzeOnHeads, ConfuseOnHeads)


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (HAUNTER_DECK_A, HAUNTER_DECK_B) if seed % 2 == 0 else (HAUNTER_DECK_B, HAUNTER_DECK_A)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def blocked(pokemon):
    c = pokemon.conditions
    return c.asleep or c.paralyzed or c.confused


def gas_on(state):
    return any(card_id(state, pk) == MUK and not blocked(pk) for p in state.players for pk in p.in_play())


def working(state, pokemon):
    """「とうめい」がはたらいているか（エンジンの関数を使わない。p.160・p.48）。"""
    return pokemon is not None and card_id(state, pokemon) == HAUNTER and not blocked(pokemon) and not gas_on(state)


def affordable(state, player):
    active = state.players[player].active
    definition = state.card_def(active.card)
    return [a.index for a in definition.attacks if a.supported and can_pay_cost(a.cost, state.energy_types(active))]


def gastly_attack(state, player):
    """ゴースのワザ: トラッシュにエネルギーカードがあり番の番号が 3 の倍数ならエナジーへんかん、そうでなくしたでなめる。"""
    usable = affordable(state, player)
    energy_in_discard = any(state.card_def(uid).category == "energy" for uid in state.players[player].discard)
    if 1 in usable and energy_in_discard and state.turn_number % 3 == 0:
        return UseAttack(player, 1)
    if 0 in usable:
        return UseAttack(player, 0)
    return UseAttack(player, 1) if 1 in usable else None


def alternative_attack(state, player, tried):
    """T19b で止まったワザのほかに使えるワザ（止まる種類でないもの）。"""
    active = state.players[player].active
    for index in affordable(state, player):
        effect = state.effects.attack_entry(card_id(state, active), index).effect
        if ("attack_index", index) not in tried and not isinstance(effect, EFFECT_COIN_TYPES):
            return UseAttack(player, index)
    return None


def policy_command(state, *, janken_winner, cure, tried):
    if state.phase is Phase.DECISION and state.decision.kind == RECOVER_ENERGY:
        d = state.decision
        return ResolveDecision(d.player, d.id, d.options[: 1 if state.turn_number % 9 == 0 else d.max_choices])
    command = muk_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    if isinstance(command, (UseAttack, EndTurn)) and state.turn_number % DECLARE_EVERY == 0 and "declare_transparency" not in tried:
        ghost = next((pk for pk in state.players[player].in_play() if card_id(state, pk) == HAUNTER), None)
        if ghost is not None:
            tried.add("declare_transparency")
            return UsePokemonPower(player, ghost.pokemon_id, 0)
    if isinstance(command, UseAttack) and card_id(state, state.players[player].active) == GASTLY:
        command = gastly_attack(state, player) or command
    if isinstance(command, UseAttack) and "evaded_coin" in tried:
        return alternative_attack(state, player, tried) or EndTurn(player)
    return command


def play_game(seed, *, cure=True, max_steps=10000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・場面の観測を返す。"""
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
                observed["rejected"] += 1
                if isinstance(command, UsePokemonPower):
                    kind = card_id(state, state.find_pokemon(command.pokemon)[1])
                    if error.code == "POWER_NOT_DECLARABLE" and kind in (HAUNTER, MUK):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code == EVADED_COIN:
                    # T19b: 相手の対戦ポケモンのゴーストの「とうめい」がはたらいているとき（エンジンとは別に場から確かめる）
                    target = state.players[1 - state.current_player].active
                    effect = state.effects.attack_entry(card_id(state, state.players[state.current_player].active), command.attack_index).effect
                    if not (working(state, target) and isinstance(effect, EFFECT_COIN_TYPES)):
                        raise AssertionError(f"「とうめい」がはたらいていない・止める種類のワザでないのに {EVADED_COIN}: {command}")
                    observed[f"stopped_attack_{EVADED_COIN}"] += 1
                    turn_tried.update({"evaded_coin", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, AttachEnergy):
                    if error.code != R13:
                        raise
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
                    continue
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
        observed["accepted"] += 1
        if isinstance(command, UseAttack):
            observe_attack(state, new, observed)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def observe_attack(state, new, observed):
    """受け付けたワザのログを、ワザの前の場から求めた「とうめい」と比べて数える。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    checks = [e for e in events if e["kind"] == "evade_check"]
    player = state.current_player
    target = state.players[1 - player].active
    actives = {p.active.pokemon_id for p in state.players if p.active is not None}
    for check in checks:
        owner, pokemon = state.find_pokemon(check["pokemon_id"])
        if not working(state, pokemon) or owner != check["player"]:
            raise AssertionError(f"はたらいていない「とうめい」・ゴースト側でないプレイヤーの判定: {check}")
        if check["pokemon_id"] not in actives:
            observed["evade_on_bench"] += 1
    if target is not None and card_id(state, target) == HAUNTER:
        if blocked(target):
            observed["haunter_attacked_while_blocked"] += 1
        elif gas_on(state):
            observed["haunter_attacked_under_gas"] += 1
        else:
            observed["haunter_attacked_working"] += 1
            if not checks:
                observed["haunter_attacked_working_no_coin"] += 1  # 最終ダメージが 0（抵抗力・ディフェンダー）で効果もない・こんらんの「うら」
        if (blocked(target) or gas_on(state)) and checks:
            raise AssertionError(f"力が消えているゴーストの判定: {checks}")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attack" and state.cards[e["pokemon"]].card_id in (GASTLY, HAUNTER):
            counted[f"attack_{e['attack']}"] += 1
        elif kind == "evade_check":
            counted["evade_check"] += 1
            counted[f"evade_check_{e['result']}"] += 1
            counted[f"evade_check_first_{e['element']}"] += 1
        elif kind == "attack_evaded":
            counted[f"evaded_{e['element']}"] += 1
            if e["element"] == "damage":
                counted["evaded_damage_total"] += e["amount"]
        elif kind == "recover_energy":
            counted["recover_energy"] += 1
            counted["recover_energy_cards"] += len(e["cards"])
        elif kind == "knock_out" and state.cards[e["pokemon"]].card_id == HAUNTER:
            counted["knock_out_haunter"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 自然な対戦（SEEDS の 80 局）で数えた回数（v0.9）。手順・デッキ・乱数の使い方が変わると変わる。止まった 1 局は対戦準備の切り直しの
# 補償（v0.1 からの未解決）。ゴーストへの進化 161 回。ワザの前の場で、相手の対戦ポケモンがゴーストだったワザ: 「とうめい」がはたらいて
# いた 228 回（判定 207 回・最終ダメージが 0 で効果もないなど判定なし 21 回）・かがくへんかガスで消えていた 91 回・ねむり・マヒ・こんらんで
# 消えていた 15 回。判定 207 回（「おもて」97・「うら」110。最初に受けた要素: ダメージ 140・ねむり 57・どく 9・マヒ 1）。受けなかった
# ダメージ 56 件・合計 940、受けなかった効果: ねむり 42・どく 8・入れ替え 2・マヒ 1。ベンチでの判定 0 回（ベンチにダメージや効果を与える
# ワザが対応カードにない。T7・T25 は盤面を直接作ったテストで確かめる）。T19b で止めたワザ 43 回。「とうめい」の宣言の拒否 311 回。
EXPECTED_COUNTS = {
    "accepted": 9473, "attack_あくむ": 659, "attack_したでなめる": 122, "attack_エナジーへんかん": 11, "evade_check": 207,
    "evade_check_first_damage": 140, "evade_check_first_paralysis": 1, "evade_check_first_poison": 9, "evade_check_first_sleep": 57,
    "evade_check_heads": 97, "evade_check_tails": 110, "evaded_damage": 56, "evaded_damage_total": 940, "evaded_forced_switch": 2,
    "evaded_paralysis": 1, "evaded_poison": 8, "evaded_sleep": 42, "evolve_to_PMCG1-003": 29, "evolve_to_PMCG1-008": 70,
    "evolve_to_PMCG2-007": 23, "evolve_to_PMCG3-007": 58, "evolve_to_PMCG3-030": 161, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 1,
    "haunter_attacked_under_gas": 91, "haunter_attacked_while_blocked": 15, "haunter_attacked_working": 228,
    "haunter_attacked_working_no_coin": 21, "knock_out_haunter": 38, "phase_game_over": 79, "phase_halted": 1, "recover_energy": 10,
    "recover_energy_cards": 16, "rejected": 1302, "rejected_attack_POKEMON_ASLEEP": 215, "rejected_attack_POKEMON_PARALYZED": 54,
    "rejected_declare_PMCG3-007": 82, "rejected_declare_PMCG3-030": 311, "rejected_evolve2_EVOLVED_THIS_TURN": 20,
    "rejected_evolve_FIRST_TURN_EVOLUTION": 56, "rejected_evolve_PLAYED_THIS_TURN": 120, "rejected_retreat_POKEMON_ASLEEP": 322,
    "rejected_retreat_POKEMON_PARALYZED": 79, "stopped_attack_UNRESOLVED_EVADED_EFFECT_COIN": 43, "take_prize": 480,
}

# 「とうめい」の「おもて」「うら」（ダメージの要素）・受けなかったどく・かがくへんかガスで消えたゴーストへのワザ・ねむりなどで消えた
# ゴーストへのワザ・T19b の停止がある対戦
GOLDEN_SEED = 11
GOLDEN_SHAPE = (172, 61, Phase.GAME_OVER)
GOLDEN_DIGEST = "f0ffb5ade1b2eefe7dfa5c9a8c8124d2b17b296d3c763805a237354fc4037c47"
RECOVER_SEED = 61  # エナジーへんかんで 1 枚・2 枚を手札に加える対戦


class FullGameWithHaunterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        return counted

    def test_counts(self):
        """自然な対戦の中で、「とうめい」が「おもて」「うら」の両方ではたらき、ダメージと効果（どく・ねむり・マヒ・入れ替え）を受けず、
        かがくへんかガス・特殊状態で消え、T19b で止まる（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG3-030", "evade_check_heads", "evade_check_tails", "evaded_damage", "haunter_attacked_under_gas",
                    "haunter_attacked_while_blocked", "haunter_attacked_working_no_coin", f"stopped_attack_{EVADED_COIN}",
                    "rejected_declare_PMCG3-030", "attack_あくむ", "attack_したでなめる", "attack_エナジーへんかん", "recover_energy",
                    "knock_out_haunter", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["evade_check"], counted["evade_check_heads"] + counted["evade_check_tails"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（「とうめい」の判定と、その時点の場・コイン・受けたダメージと効果の対応を含む）・書き出しの監査
        （形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        """対戦準備のあとの乱数はコインだけ（「とうめい」のコインも 1 枚 1 回）。「とうめい」のコインの数は判定の数と同じ。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))
                power = [e for e in coin_events(state) if e["source"] == "power"]
                self.assertEqual(len(power), sum(1 for e in state.log if e["kind"] == "evade_check"))

    def test_replay(self):
        for seed in SEEDS[:3]:
            state, commands, _ = self.games[seed]
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))


class GoldenHaunterGameTest(unittest.TestCase):
    """「とうめい」が「おもて」「うら」の両方ではたらく対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.9）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evade_check_heads", "evade_check_tails", "evaded_damage"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.9")
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class LogAuditTransparencyTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、「とうめい」のログの食い違いを見つけること（監査が何でも通すのではないことの確認。D6）。
    GOLDEN_SEED の対戦のログを書きかえて、それぞれの種類の誤りを報告することを確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        log = cls.state.log
        cls.heads = next(i for i, e in enumerate(log) if e["kind"] == "evade_check" and e["evaded"] and e["element"] == "damage")
        cls.tails = next(i for i, e in enumerate(log) if e["kind"] == "evade_check" and not e["evaded"] and e["element"] == "damage")

    def broken(self, change_log):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        change_log(log)
        state.log = tuple(log)
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError, TypeError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def assert_reported(self, change_log, text):
        problems = self.broken(change_log)
        self.assertTrue(any(text in p for p in problems), problems)

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])

    def test_1_missing_check(self):
        """「うら」の判定とコインを消すと、はたらいている「とうめい」のゴーストが判定なしでダメージを受けたことになる。"""
        def drop(log):
            del log[self.tails - 1:self.tails + 1]

        self.assert_reported(drop, "判定（evade_check）なしで受けた")

    def test_2_result_differs_from_the_coin(self):
        def flip(log):
            log[self.heads] = {**log[self.heads], "result": "tails"}

        self.assert_reported(flip, "同じ結果のコインがない")

    def test_3_missing_coin(self):
        def drop(log):
            del log[self.heads - 1]

        self.assert_reported(drop, "同じ結果のコインがない")

    def test_4_damage_after_heads(self):
        """「おもて」のあとに、そのポケモンへのダメージを書き足すと報告する（受けないと決まったポケモンが受けた）。"""
        def add(log):
            evaded = log[self.heads + 1]
            log[self.heads + 1] = {"kind": "damage", "turn": evaded["turn"], "player": evaded["player"], "pokemon": evaded["pokemon"],
                                   "amount": evaded["amount"], "steps": (), "weakness": False, "resistance": False,
                                   "total_damage": evaded["amount"]}

        self.assert_reported(add, "のすぐあとが damage")

    def test_5_two_checks_in_one_attack(self):
        def duplicate(log):
            log.insert(self.heads + 1, dict(log[self.heads]))
            log.insert(self.heads + 1, dict(log[self.heads - 1]))

        self.assert_reported(duplicate, "2 回以上")

    def test_6_check_while_asleep(self):
        """判定の前に、そのゴーストをねむりにしたログを書き足すと、力が消えているのに判定したことになる。"""
        def sleep(log):
            check = log[self.heads]
            attack = max(i for i in range(self.heads) if log[i]["kind"] == "attack")
            log.insert(attack, {"kind": "special_condition", "turn": check["turn"], "player": check["player"], "pokemon": check["pokemon"],
                                "pokemon_id": check["pokemon_id"], "condition": "sleep", "effect": "test"})

        self.assert_reported(sleep, "で力が消えている「とうめい」")

    def test_7_check_by_a_pokemon_without_the_power(self):
        def other(log):
            log[self.heads] = {**log[self.heads], "power": "PMCG1-060@power0"}

        self.assert_reported(other, "と違う")

    def test_8_check_outside_an_attack(self):
        def move(log):
            coin, check = log[self.heads - 1], log[self.heads]
            attack = max(i for i in range(self.heads) if log[i]["kind"] == "attack")
            del log[self.heads - 1:self.heads + 1]
            log[attack:attack] = [coin, check]

        self.assert_reported(move, "ワザ")

    def test_9_evaded_without_heads(self):
        """「うら」の判定のあとに受けなかった要素を書き足すと報告する。"""
        def add(log):
            check = log[self.tails]
            log.insert(self.tails + 2, {"kind": "attack_evaded", "turn": check["turn"], "player": check["player"], "pokemon": check["pokemon"],
                                        "pokemon_id": check["pokemon_id"], "effect": check["effect"], "element": "sleep"})

        self.assert_reported(add, "「おもて」の判定がない")

    def test_10_evaded_zero_damage(self):
        def zero(log):
            log[self.heads + 1] = {**log[self.heads + 1], "amount": 0}

        self.assert_reported(zero, "0 より大きいはず")

    def test_11_coin_by_the_attacker(self):
        """コインと判定をワザを使ったプレイヤーのものにすると報告する（コイントスはゴースト側のプレイヤー。T33）。"""
        def attacker(log):
            for i in (self.heads - 1, self.heads):
                log[i] = {**log[i], "player": 1 - log[i]["player"]}

        self.assert_reported(attacker, "判定したプレイヤーの場のポケモンではない")

    def test_13_tails_but_the_damage_removed(self):
        """「うら」なのにダメージを消す（damage を attack_evaded に書きかえる）と報告する（D6 の 4）。"""
        def remove(log):
            check, damage = log[self.tails], log[self.tails + 1]
            log[self.tails + 1] = {"kind": "attack_evaded", "turn": damage["turn"], "player": damage["player"], "pokemon": damage["pokemon"],
                                   "pokemon_id": check["pokemon_id"], "effect": check["effect"], "element": "damage", "amount": damage["amount"]}

        self.assert_reported(remove, "のすぐあとが attack_evaded")

    def test_14_check_while_the_gas_works(self):
        """判定の前に、ベトベトンがベンチに出たログを書き足すと、かがくへんかガスがはたらいているのに判定したことになる（D6 の 6）。"""
        muk = next(uid for uid, card in self.state.cards.items() if card.card_id == MUK)

        def gas(log):
            attack = max(i for i in range(self.heads) if log[i]["kind"] == "attack")
            log.insert(attack, {"kind": "play_to_bench", "turn": log[attack]["turn"], "player": self.state.cards[muk].owner, "card": muk})

        self.assert_reported(gas, "かがくへんかガス（ポケモン")

    def test_15_coin_after_the_check(self):
        """判定とコインの順番を入れかえると報告する（D6 の 7）。"""
        def swap(log):
            log[self.heads - 1], log[self.heads] = log[self.heads], log[self.heads - 1]

        self.assert_reported(swap, "同じ結果のコインがない")

    def test_16_damage_differs_from_the_log(self):
        """「うら」で受けたダメージの量を書きかえると、ログから組み立てたダメージと合わない（D6 の 8）。"""
        def more(log):
            damage = log[self.tails + 1]
            log[self.tails + 1] = {**damage, "amount": damage["amount"] + 10}

        self.assert_reported(more, "ログから組み立てた")

    def test_17_check_for_another_pokemon(self):
        """判定のポケモンの番号を、同じプレイヤーの別の場のポケモンに書きかえると報告する（D6 の 9）。"""
        def other(log):
            check = log[self.heads]
            ids = sorted({e["pokemon_id"] for e in log[:self.heads] if e.get("player") == check["player"] and "pokemon_id" in e
                          and e["pokemon_id"] != check["pokemon_id"]})
            for i in (self.heads - 1, self.heads):
                log[i] = {**log[i], "pokemon_id": ids[0]}

        problems = self.broken(other)
        self.assertTrue(any("「とうめい」" in p or "判定" in p for p in problems), problems)

    def test_12_recover_energy_not_in_the_discard(self):
        """エナジーへんかんで手札に加えたカードを、トラッシュになかったカードに書きかえると報告する（RECOVER_SEED の対戦）。"""
        state = play_game(RECOVER_SEED, cure=RECOVER_SEED % 3 != 0)[0]
        self.assertEqual(log_problems(state), [])
        index = next(i for i, e in enumerate(state.log) if e["kind"] == "recover_energy")
        broken = state.clone()
        log = [dict(e) for e in broken.log]
        log[index] = {**log[index], "cards": (*log[index]["cards"][1:], 10 ** 6)}
        broken.log = tuple(log)
        problems = log_problems(broken)
        self.assertTrue(any("トラッシュのエネルギーカードにない" in p for p in problems), problems)


class HaunterStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py のゴーストの組。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。"""

    def test_small_haunter_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        scenarios = [s for s in stress.POWER_SCENARIOS if s.name.startswith("haunter")]
        self.assertEqual(len(scenarios), 2)
        result = stress.run(scenarios, range(2), steps=300, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 4)
        for key in ("code:POWER_NOT_DECLARABLE", "observed:evade_check"):
            self.assertGreater(counts.get(key, 0), 0, (key, counts))
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


if __name__ == "__main__":
    unittest.main()
