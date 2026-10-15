"""ワンリキー → ゴーリキー → カイリキー（v0.10）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

カイリキーのポケモンパワー「はんげき」（相手のワザによってダメージを受けたときに自動的にはたらき、ダメージを与えたポケモンに、弱点・抵抗力に
関係なく 10 ダメージ。きぜつしても与える。ダメージを受けるとき、すでにねむり・マヒ・こんらんなら、はたらかない）が、自然な対戦の中で、
いろいろなワザ（ダメージだけ・でんげき・ふきとばし・メガドレイン・やどりぎのタネ・どくのこな・いとをはく・ねんりき（弱点）・あくむ・
ヘドロこうげき・ちきゅうなげ（ミラー）・からてチョップ・じごくぐるま）を受けるときにはたらくこと、かがくへんかガス（v0.8）と特殊状態で
消えること、ワザを使ったポケモンをきぜつさせること、きぜつしたカイリキーも与えること、原典で決められない場合（C18）で止まることを確かめる。

- 一方のデッキは、ワンリキー・ゴーリキー・カイリキーとエビワラー。
- もう一方のデッキは、カイリキーに使うワザの種類を多くした（フシギダネ・フシギソウ・バタフリー・ピカチュウ・ケーシィ・ロケット団の
  ベトベター・ベトベトン・ゴース・ゴースト・ワンリキー・ゴーリキー・カイリキー（ミラー））。

自然な対戦の中で起こる出来事の回数を数えて固定する（docs/v0.10-verification.md 4 章）。盤面を直接作ったテスト
（tests/test_counterattack_v0_10.py）とは別に数える。根拠のページは tests/test_counterattack_v0_10.py（p.89・p.138・p.192・p.245・
p.309・p.311・p.319〜p.324）・tests/test_machamp_line_v0_10.py（p.186・p.189・p.190・p.192）。手順は tests/test_haunter_games_v0_9.py の
``policy_command`` に、次を加えたもの（対戦相手の AI ではない）:

- 番の番号が 7 の倍数の番は、自分の場にカイリキーがいれば一度だけ、「はんげき」の使用を試す（宣言しない特殊能力。``POWER_NOT_DECLARABLE``）。
- ワザが ``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT``（C18）で止まったら、その番はほかの使えるワザ（試していないもの）を 1 度だけ試し、
  なければ番を終える。

「はんげき」がはたらいているかは、エンジンの関数を使わずに場から求める（``working``。カイリキー（いちばん上のカード）が、ねむり・マヒ・
こんらんでなく、場のベトベトン（いちばん上のカード）のうち、ねむり・マヒ・こんらんでないものがいない）。ワザ（と決定の答え）を
受け付けるたびに、ワザの前の場で ``working`` のポケモンが相手のワザのダメージ（0 より大きい）を受けたときだけ、「はんげき」のログが
あることを確かめる。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    ABRA, BILL, BULBASAUR, BUTTERFREE, CATERPIE, DEFENDER, FIGHTING, GASTLY, GRASS, GRIMER, HAUNTER, HITMONCHAN, IVYSAUR, LIGHTNING,
    MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PLUSPOWER, POTION, PSYCHIC, SWITCH, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_haunter_games_v0_9 import EFFECT_COIN_TYPES, EVADED_COIN, affordable, blocked, card_id, gas_on
from tests.test_haunter_games_v0_9 import policy_command as haunter_policy_command
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# ワンリキー・ゴーリキー・カイリキーとエビワラー
MACHAMP_DECK_A = expand_decklist({
    MACHOP: 4, MACHOKE: 4, MACHAMP: 3, HITMONCHAN: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2, FIGHTING: 35,
})
# カイリキーに使うワザの種類を多くしたデッキ（少しのベトベトン・ゴースト・カイリキー）
MACHAMP_DECK_B = expand_decklist({
    BULBASAUR: 3, IVYSAUR: 2, CATERPIE: 2, METAPOD: 1, BUTTERFREE: 2, PIKACHU: 2, ABRA: 2, GRIMER: 2, MUK: 1, GASTLY: 2, HAUNTER: 1,
    MACHOP: 2, MACHOKE: 1, MACHAMP: 1, PLUSPOWER: 2, BILL: 4, GRASS: 18, LIGHTNING: 3, PSYCHIC: 6, FIGHTING: 3,
})
SEEDS = tuple(range(80))
DECLARE_EVERY = 7  # 手順の決まりごと（ルールの制限ではない）
DOUBLE_KO = "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (MACHAMP_DECK_A, MACHAMP_DECK_B) if seed % 2 == 0 else (MACHAMP_DECK_B, MACHAMP_DECK_A)


def working(state, pokemon):
    """「はんげき」がはたらいているか（エンジンの関数を使わない。p.192・p.48）。"""
    return pokemon is not None and card_id(state, pokemon) == MACHAMP and not blocked(pokemon) and not gas_on(state)


def alternative_attack(state, player, tried):
    """止まったワザのほかに使えるワザ（試していないもの。T19b で止まる種類は相手がゴーストのとき除く）。"""
    target = state.players[1 - player].active
    for index in affordable(state, player):
        effect = state.effects.attack_entry(card_id(state, state.players[player].active), index).effect
        if ("attack_index", index) in tried:
            continue
        if evasion_working(state, target) and isinstance(effect, EFFECT_COIN_TYPES):
            continue
        return UseAttack(player, index)
    return None


def policy_command(state, *, janken_winner, cure, tried):
    command = haunter_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    if isinstance(command, (UseAttack, EndTurn)) and state.turn_number % DECLARE_EVERY == 0 and "declare_strikes_back" not in tried:
        machamp = next((pk for pk in state.players[player].in_play() if card_id(state, pk) == MACHAMP), None)
        if machamp is not None:
            tried.add("declare_strikes_back")
            return UsePokemonPower(player, machamp.pokemon_id, 0)
    if isinstance(command, UseAttack) and ("counter_double" in tried or ("attack_index", command.attack_index) in tried):
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
                    if error.code == "POWER_NOT_DECLARABLE" and kind in (HAUNTER, MUK, MACHAMP):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code == DOUBLE_KO:
                    # C18: 相手の対戦ポケモンのカイリキーの「はんげき」がはたらいているとき（エンジンとは別に場から確かめる）
                    target = state.players[1 - state.current_player].active
                    if not working(state, target):
                        raise AssertionError(f"「はんげき」がはたらいていないのに {DOUBLE_KO}: {command}")
                    observed[f"stopped_attack_{DOUBLE_KO}"] += 1
                    turn_tried.update({"counter_double", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == EVADED_COIN:
                    target = state.players[1 - state.current_player].active
                    if not evasion_working(state, target):
                        raise AssertionError(f"「とうめい」がはたらいていないのに {EVADED_COIN}: {command}")
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
        if isinstance(command, (UseAttack, ResolveDecision)):
            observe_counter(state, new, command, observed)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def observe_counter(state, new, command, observed):
    """受け付けたワザ（と決定の答え）のログを、ワザの前の場から求めた「はんげき」と比べて数える。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    attacker_player = state.current_player
    owners = {pk.pokemon_id: player for player, p in enumerate(state.players) for pk in p.in_play()}
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    due = []
    for e in events:
        if e["kind"] == "damage" and e["amount"] > 0:
            pokemon = by_card.get(e["pokemon"])
            if pokemon is not None and owners[pokemon.pokemon_id] != attacker_player and working(state, pokemon):
                due.append(pokemon.pokemon_id)
                if e["total_damage"] >= state.card_def(pokemon.card).hp:
                    observed["counter_from_knocked_out_machamp"] += 1
                if state.players[owners[pokemon.pokemon_id]].active is not pokemon:
                    observed["counter_on_bench"] += 1
        elif e["kind"] in ("counterattack", "counterattack_skipped"):
            if not due or due.pop(0) != e["pokemon_id"]:
                raise AssertionError(f"はたらくはずのない「はんげき」: {e}")
            if e["attacker_pokemon_id"] != state.players[attacker_player].active.pokemon_id:
                raise AssertionError(f"「はんげき」の相手がワザを使ったポケモンではない: {e}")
    if due:
        raise AssertionError(f"はたらいた「はんげき」のログがない: {due}")
    if isinstance(command, UseAttack):
        target = state.players[1 - attacker_player].active
        if target is not None and card_id(state, target) == MACHAMP:
            if blocked(target):
                observed["machamp_attacked_while_blocked"] += 1
            elif gas_on(state):
                observed["machamp_attacked_under_gas"] += 1
            else:
                observed["machamp_attacked_working"] += 1


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    knocked_in_attack = []
    for e in state.log:
        kind = e["kind"]
        if kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attack":
            knocked_in_attack = []
            if state.cards[e["pokemon"]].card_id in (MACHOP, MACHOKE, MACHAMP):
                counted[f"attack_{e['attack']}"] += 1
        elif kind == "counterattack":
            counted["counterattack"] += 1
            counted["counterattack_damage_total"] += e["amount"]
            if e["knocked_out"]:
                counted["counterattack_knock_out"] += 1
        elif kind == "counterattack_skipped":
            counted["counterattack_skipped"] += 1
        elif kind == "drain_heal_skipped":
            counted["drain_heal_skipped"] += 1
        elif kind == "knock_out":
            knocked_in_attack.append(e)
            if state.cards[e["pokemon"]].card_id == MACHAMP:
                counted["knock_out_machamp"] += 1
            if e.get("simultaneous"):
                counted["knock_out_simultaneous"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.GAME_OVER:
        counted["decisive"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 自然な対戦（SEEDS の 80 局）で数えた回数（v0.10）。手順・デッキ・乱数の使い方が変わると変わる。止まった 1 局は対戦準備の切り直しの
# 補償（v0.1 からの未解決）。カイリキーへの進化 50 回。ワザの前の場で、相手の対戦ポケモンがカイリキーだったワザ: 「はんげき」がはたらいて
# いた 77 回・かがくへんかガスで消えていた 3 回・ねむり・マヒ・こんらんで消えていた 1 回。「はんげき」67 回（合計 670。ワザを使った
# ポケモンをきぜつさせた 11 回・そのダメージできぜつしたカイリキーの「はんげき」2 回。与えなかった（相手がすでに HP 以上）0 回・ベンチの
# カイリキー 0 回（ベンチにダメージを与えるワザが対応カードにない））。C18 で止めたワザ 1 回。「はんげき」の宣言の拒否 40 回。
EXPECTED_COUNTS = {
    "accepted": 5124, "attack_からてチョップ": 21, "attack_けたぐり": 181, "attack_じごくぐるま": 49, "attack_ちきゅうなげ": 114,
    "counter_from_knocked_out_machamp": 2, "counterattack": 67, "counterattack_damage_total": 670, "counterattack_knock_out": 11,
    "decisive": 79, "evolve_to_PMCG1-003": 8, "evolve_to_PMCG1-008": 40, "evolve_to_PMCG1-055": 99, "evolve_to_PMCG1-057": 50,
    "evolve_to_PMCG2-007": 4, "evolve_to_PMCG3-007": 12, "evolve_to_PMCG3-030": 17, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 1,
    "knock_out_machamp": 3, "knock_out_simultaneous": 6, "machamp_attacked_under_gas": 3, "machamp_attacked_while_blocked": 1,
    "machamp_attacked_working": 77, "phase_game_over": 79, "phase_halted": 1, "rejected": 364, "rejected_attack_POKEMON_ASLEEP": 9,
    "rejected_attack_POKEMON_PARALYZED": 70, "rejected_declare_PMCG1-057": 40, "rejected_declare_PMCG3-007": 6,
    "rejected_declare_PMCG3-030": 25, "rejected_evolve2_EVOLVED_THIS_TURN": 38, "rejected_evolve_FIRST_TURN_EVOLUTION": 62,
    "rejected_evolve_PLAYED_THIS_TURN": 63, "rejected_retreat_POKEMON_ASLEEP": 9, "rejected_retreat_POKEMON_PARALYZED": 41,
    "stopped_attack_UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT": 1, "take_prize": 344,
}

# 「はんげき」が 4 回はたらき、そのうち 1 回でワザを使ったポケモンがきぜつする対戦
GOLDEN_SEED = 65
GOLDEN_SHAPE = (81, 27, Phase.GAME_OVER)
GOLDEN_DIGEST = "8eb22ba80c945505e3f53f7799146db938bdd79b896066b5b2f05bed477fccde"


class FullGameWithMachampTest(unittest.TestCase):
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
        """自然な対戦の中で、「はんげき」がはたらき、ワザを使ったポケモンをきぜつさせ、きぜつしたカイリキーも与え、かがくへんかガス・特殊状態で
        消え、C18 で止まる（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG1-057", "counterattack", "counterattack_knock_out", "counter_from_knocked_out_machamp",
                    "machamp_attacked_under_gas", "machamp_attacked_while_blocked", "rejected_declare_PMCG1-057", "knock_out_machamp",
                    "attack_ちきゅうなげ", "attack_からてチョップ", "attack_じごくぐるま", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["counterattack_damage_total"], 10 * counted["counterattack"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（「はんげき」とその時点の場・順番・ダメージの対応を含む）・書き出しの監査（形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        """対戦準備のあとの乱数はコインだけ（「はんげき」は乱数を使わない）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay(self):
        for seed in SEEDS[:3]:
            state, commands, _ = self.games[seed]
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))


class GoldenMachampGameTest(unittest.TestCase):
    """「はんげき」がはたらき、きぜつさせる対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.10）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("counterattack", "counterattack_knock_out"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.11・v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class LogAuditCounterattackTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、「はんげき」のログの食い違いを見つけること（監査が何でも通すのではないことの確認。D7）。
    GOLDEN_SEED の対戦のログ（キャタピーの「いとをはく」に「はんげき」4 回。4 回目でキャタピーがきぜつ）を書きかえて、それぞれの種類の誤りを
    報告することを確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        log = cls.state.log
        cls.first = next(i for i, e in enumerate(log) if e["kind"] == "counterattack")
        cls.knock = next(i for i, e in enumerate(log) if e["kind"] == "counterattack" and e["knocked_out"])
        cls.attack = max(i for i in range(cls.first) if log[i]["kind"] == "attack")

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
        self.assertEqual(self.state.log[self.first - 1]["kind"], "damage")

    def test_1_missing_counter(self):
        """はたらいた「はんげき」を消すと、効果（コイン・特殊状態）・番の終わりより先にないことになる。"""
        def drop(log):
            del log[self.first]

        self.assert_reported(drop, "より先に")

    def test_2_counter_while_asleep(self):
        """ワザの前に、カイリキーをねむりにしたログを書き足すと、はたらく理由なしの「はんげき」になる（C19）。"""
        def sleep(log):
            counter = log[self.first]
            log.insert(self.attack, {"kind": "special_condition", "turn": counter["turn"], "player": counter["player"],
                                     "pokemon": counter["pokemon"], "pokemon_id": counter["pokemon_id"], "condition": "sleep", "effect": "test"})

        self.assert_reported(sleep, "はたらく理由")

    def test_3_wrong_amount(self):
        def double(log):
            log[self.first] = {**log[self.first], "amount": 20, "total_damage": log[self.first]["total_damage"] + 10}

        self.assert_reported(double, "登録の 10 と違う")

    def test_4_wrong_target(self):
        def other(log):
            log[self.first] = {**log[self.first], "attacker_pokemon_id": log[self.first]["pokemon_id"]}

        self.assert_reported(other, "ワザの処理の中にない")

    def test_5_counter_before_the_damage(self):
        def swap(log):
            log[self.first - 1], log[self.first] = log[self.first], log[self.first - 1]

        self.assert_reported(swap, "はたらく理由")

    def test_6_counter_after_the_turn_end(self):
        """「はんげき」を番の終わりのあとに動かすと、番の終わり（と効果）より先にないことになり、ワザの外の「はんげき」になる。"""
        def move(log):
            counter = log.pop(self.first)
            end = next(i for i in range(self.first, len(log)) if log[i]["kind"] == "turn_end")
            log.insert(end + 1, counter)

        problems = self.broken(move)
        self.assertTrue(any("より先に" in p for p in problems), problems)
        self.assertTrue(any("ワザの処理の中にない" in p for p in problems), problems)

    def test_7_two_counters(self):
        def duplicate(log):
            log.insert(self.first + 1, dict(log[self.first]))

        problems = self.broken(duplicate)
        self.assertTrue(any("「はんげき」が 2 回" in p for p in problems), problems)

    def test_8_counter_by_the_attackers_own_pokemon(self):
        """「はんげき」を、ワザを使った側のポケモンのものに書きかえると報告する（相手のワザのダメージを受けたポケモンのものではない。C3・C4）。"""
        def own(log):
            counter = log[self.first]
            log[self.first] = {**counter, "player": counter["attacker"], "pokemon": counter["attacker_pokemon"],
                               "pokemon_id": counter["attacker_pokemon_id"]}

        self.assert_reported(own, "ダメージを受けたポケモン")

    def test_9_counter_while_the_gas_works(self):
        """ワザの前に、ベトベトンがベンチに出たログを書き足すと、かがくへんかガスがはたらいているのに「はんげき」があることになる（C24）。"""
        muk = next(uid for uid, card in self.state.cards.items() if card.card_id == MUK)

        def gas(log):
            log.insert(self.attack, {"kind": "play_to_bench", "turn": log[self.attack]["turn"], "player": self.state.cards[muk].owner,
                                     "card": muk})

        self.assert_reported(gas, "はたらく理由")

    def test_10_total_damage_differs(self):
        def more(log):
            log[self.first] = {**log[self.first], "total_damage": log[self.first]["total_damage"] + 10}

        self.assert_reported(more, "ログから組み立てた")

    def test_11_knock_out_mark_differs(self):
        def mark(log):
            log[self.knock] = {**log[self.knock], "knocked_out": False}

        self.assert_reported(mark, "きぜつの印")

    def test_12_skipped_although_not_knocked_out(self):
        """与えた「はんげき」を「与えなかった」（counterattack_skipped）に書きかえると報告する（C15 は相手がすでに HP 以上のときだけ）。"""
        def skip(log):
            counter = log[self.first]
            log[self.first] = {k: v for k, v in counter.items() if k not in ("amount", "total_damage", "knocked_out")} | {
                "kind": "counterattack_skipped", "reason": "knocked_out"}

        self.assert_reported(skip, "きぜつしていない相手")

    def test_13_damage_after_the_counter(self):
        """「はんげき」のあとに、同じワザのダメージの要素を書き足すと報告する（ダメージの処理のあとに与える。p.89）。"""
        def add(log):
            damage = log[self.first - 1]
            log.insert(self.first + 1, {**damage, "amount": 0, "total_damage": damage["total_damage"]})

        self.assert_reported(add, "あとにダメージの要素")

    def test_14_another_knock_out_with_the_counter_knock_out(self):
        """「はんげき」でワザを使ったポケモンがきぜつしたワザで、ほかのポケモンもきぜつしたことにすると報告する（C18 は止めるはず）。"""
        def both(log):
            counter = log[self.knock]
            ko = next(i for i in range(self.knock, len(log)) if log[i]["kind"] == "knock_out")
            log.insert(ko, {"kind": "knock_out", "turn": counter["turn"], "player": counter["player"], "pokemon": counter["pokemon"],
                            "discarded_energy": ()})

        self.assert_reported(both, "同時のきぜつか決められない")

    def test_15_heal_after_the_counter_knock_out(self):
        """「はんげき」できぜつしたポケモンのダメージカウンターをとりのぞいたことにすると報告する（C16）。"""
        def heal(log):
            counter = log[self.knock]
            log.insert(self.knock + 1, {"kind": "drain_heal", "turn": counter["turn"], "player": counter["attacker"],
                                        "pokemon": counter["attacker_pokemon"], "pokemon_id": counter["attacker_pokemon_id"],
                                        "effect": counter["effect"], "dealt": 10, "drain_counters": 0, "counters": 0, "amount": 0,
                                        "damage_before": counter["total_damage"], "total_damage": counter["total_damage"]})

        self.assert_reported(heal, "C16")

    def test_16_knock_out_before_the_counter(self):
        """「はんげき」できぜつしたポケモンのきぜつ（knock_out）を「はんげき」より前に動かすと報告する（きぜつの処理はワザのあと。p.89・p.309）。"""
        def move(log):
            ko = next(i for i in range(self.knock, len(log)) if log[i]["kind"] == "knock_out")
            log.insert(self.knock, log.pop(ko))

        self.assert_reported(move, "より先に knock_out がある")

    def test_17_prize_taken_by_the_wrong_player(self):
        """「はんげき」のきぜつのサイドを、ワザを使ったプレイヤー（きぜつしたポケモンの持ち主）が取ったことにすると報告する（p.323。C38）。"""
        def wrong(log):
            prize = next(i for i in range(self.knock, len(log)) if log[i]["kind"] == "take_prize")
            log[prize] = {**log[prize], "player": 1 - log[prize]["player"]}

        self.assert_reported(wrong, "サイド")

    def test_18_missing_counter_of_a_knocked_out_machamp(self):
        """きぜつしたカイリキーの「はんげき」（seed 34 の自然な対戦）を消すと報告する（きぜつしても与える。C17）。"""
        state = play_game(34, cure=34 % 3 != 0)[0]
        index = next(i for i, e in enumerate(state.log) if e["kind"] == "counterattack" and any(
            later["kind"] == "knock_out" and later["pokemon"] == e["pokemon"] for later in state.log[i:i + 12]))
        self.assertEqual(log_problems(state), [])
        broken = state.clone()
        broken.log = tuple(e for i, e in enumerate(state.log) if i != index)
        self.assertTrue(any("より先に knock_out がある" in p for p in log_problems(broken)), log_problems(broken))


class MachampStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py のカイリキーの組。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。"""

    def test_small_machamp_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        scenarios = [s for s in stress.POWER_SCENARIOS if s.name.startswith("machamp")]
        self.assertEqual(len(scenarios), 2)
        result = stress.run(scenarios, range(2), steps=300, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 4)
        for key in ("code:POWER_NOT_DECLARABLE", "observed:counterattack"):
            self.assertGreater(counts.get(key, 0), 0, (key, counts))
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


if __name__ == "__main__":
    unittest.main()
