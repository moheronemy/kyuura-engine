"""ベトベター → ベトベトン（v0.8）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ベトベトンのポケモンパワー「かがくへんかガス」（常にはたらく。場にいるかぎり、「かがくへんかガス」以外のすべての特殊能力は使えず、その力も
消える。ねむり・マヒ・こんらんのとき、この力は消える）が、v0.5〜v0.7 の特殊能力（フシギバナのエナジートランス・カメックスのあまごい・
フーディンのダメージスワップ）を、自然な対戦の中で実際に消すことと、消えたあと（きぜつ・特殊状態）に、また使えることを確かめる。

- 一方のデッキは、ベトベター・ベトベトンと、フシギバナの系統・ケーシィの系統（自分のかがくへんかガスが、自分のエナジートランス・
  ダメージスワップも消す）。
- もう一方のデッキは、ケーシィの系統・ゼニガメの系統・ロコン（こんらんにして、相手のベトベトンの力を消す）と、少しのベトベトン（両方の
  プレイヤーのかがくへんかガスが同じ場にある対戦がある）。

自然な対戦の中で起こる出来事（ベトベトンへの進化・かがくへんかガスがはたらいている／消えている場面・3 つの特殊能力が消された回数・消えた
あとの使用・宣言しない特殊能力の宣言の拒否・勝敗）の回数を数えて固定する（docs/v0.8-verification.md）。盤面を直接作ったテスト
（tests/test_chemical_gas_v0_8.py）とは別に数える。

根拠のページは tests/test_chemical_gas_v0_8.py・tests/test_grimer_line_v0_8.py（p.45・p.47・p.48・p.265・p.277・p.307〜p.311・p.320〜p.324）。
手順は tests/test_alakazam_games_v0_7.py の ``policy_command`` に、次を加えたもの（対戦相手の AI ではない）:

- 使おうとした特殊能力がかがくへんかガスに消されているなら、その番に一度だけ（特殊能力の種類ごと）そのまま試す（エンジンは
  ``POWER_SUPPRESSED`` で拒否する。原典で確かめた規定なので、拒否されたことを数える）。二度目からは、特殊能力を使わない手順
  （v0.4d の手順）にもどる。
- 番の番号が 7 の倍数の番は、場にベトベトンがいれば一度だけ、かがくへんかガスの使用を試す（宣言しない特殊能力。``POWER_NOT_DECLARABLE``）。
- ベトベターのワザ: 相手の対戦ポケモンがどく状態でなく、どくガスを払えればどくガス、そうでなくねばりつくを払えればねばりつく。

かがくへんかガスがはたらいているかは、エンジンの関数を使わずに、場から求める（``gas_on``。場のベトベトン（いちばん上のカード）のうち、
ねむり・マヒ・こんらんでないものがいるか）。特殊能力を受け付けたら ``gas_on`` は偽、``POWER_SUPPRESSED`` で拒否したら真であることを、
1 手ごとに確かめる。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    apply_command,
    check_invariants,
    new_game,
    state_to_dict,
)
from kyuura_engine.cards import can_pay_cost
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    BILL,
    BLASTOISE,
    BULBASAUR,
    FIRE,
    GRASS,
    GRIMER,
    IVYSAUR,
    KADABRA,
    MUK,
    PSYCHIC,
    SQUIRTLE,
    SWITCH,
    VENUSAUR,
    VULPIX,
    WARTORTLE,
    WATER,
    best_affordable_attack,
    coin_events,
    expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_alakazam_games_v0_7 import policy_command as alakazam_policy_command
from tests.test_blastoise_games_v0_6 import R13
from tests.test_butterfree_games_v0_4d import policy_command as butterfree_policy_command
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# ベトベター・ベトベトンと、フシギバナの系統・ケーシィの系統（自分のかがくへんかガスが、自分のエナジートランス・ダメージスワップも消す）
MUK_DECK_A = expand_decklist({
    GRIMER: 4, MUK: 3, ABRA: 3, KADABRA: 2, ALAKAZAM: 2, BULBASAUR: 3, IVYSAUR: 2, VENUSAUR: 2, SWITCH: 2, BILL: 4, GRASS: 25, PSYCHIC: 8,
})
# ケーシィの系統（ねんりきでマヒ・あやしいひかりでこんらん）・ゼニガメの系統・ロコン（こんらん）と、少しのベトベトン
MUK_DECK_B = expand_decklist({
    ABRA: 4, KADABRA: 3, ALAKAZAM: 3, SQUIRTLE: 3, WARTORTLE: 2, BLASTOISE: 2, VULPIX: 4, GRIMER: 2, MUK: 1, BILL: 4, SWITCH: 2,
    PSYCHIC: 12, WATER: 8, FIRE: 8, GRASS: 2,
})
SEEDS = tuple(range(80))
POWER_USERS = (VENUSAUR, BLASTOISE, ALAKAZAM)
DECLARE_GAS_EVERY = 7  # 手順の決まりごと（ルールの制限ではない）


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (MUK_DECK_A, MUK_DECK_B) if seed % 2 == 0 else (MUK_DECK_B, MUK_DECK_A)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def blocked(pokemon):
    c = pokemon.conditions
    return c.asleep or c.paralyzed or c.confused


def gas_on(state):
    """場のベトベトン（両方のプレイヤー）のうち、ねむり・マヒ・こんらんでないものの番号（エンジンの関数を使わない。p.48）。"""
    return tuple(pk.pokemon_id for p in state.players for pk in p.in_play() if card_id(state, pk) == MUK and not blocked(pk))


def muk_in_play(state):
    return any(card_id(state, pk) == MUK for p in state.players for pk in p.in_play())


def user_kind(state, command):
    found = state.find_pokemon(command.pokemon)
    return None if found is None else card_id(state, found[1])


def grimer_attack(state, player):
    """ベトベターのワザ: 相手の対戦ポケモンがどく状態でなく、どくガス（草）を払えればどくガス、そうでなくねばりつく（草草）を払えれば
    ねばりつく、どちらでもなくどくガスを払えればどくガス。"""
    active = state.players[player].active
    gas, sticky = (can_pay_cost(a.cost, state.energy_types(active)) for a in state.card_def(active.card).attacks)
    if gas and state.players[1 - player].active.conditions.poison is None:
        return UseAttack(player, 0)
    if sticky:
        return UseAttack(player, 1)
    if gas:
        return UseAttack(player, 0)
    return None


def without_power(state, *, janken_winner, cure, tried):
    """特殊能力を使わない手順（v0.4d）。R13 で止まった番は、通常の操作をせずにワザか番の終わりへ（v0.6 の手順と同じ）。"""
    command = butterfree_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    player = state.current_player
    if isinstance(command, AttachEnergy) and "attach_blocked" in tried:
        index = best_affordable_attack(state, player)
        return EndTurn(player) if index is None else UseAttack(player, index)
    return command


def policy_command(state, *, janken_winner, cure, tried):
    command = alakazam_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    mine = state.players[player].in_play()
    if isinstance(command, (UseAttack, EndTurn)) and state.turn_number % DECLARE_GAS_EVERY == 0 and "declare_gas" not in tried:
        muk = next((pk for pk in mine if card_id(state, pk) == MUK), None)
        if muk is not None:
            tried.add("declare_gas")
            return UsePokemonPower(player, muk.pokemon_id, 0)
    if isinstance(command, UsePokemonPower) and gas_on(state):
        marker = f"suppressed:{user_kind(state, command)}"
        if marker not in tried:
            tried.add(marker)
            return command  # 一度だけ試す（POWER_SUPPRESSED）
        command = without_power(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if isinstance(command, UseAttack) and card_id(state, state.players[player].active) == GRIMER:
        command = grimer_attack(state, player) or command
    return command


def play_game(seed, *, cure=True, max_steps=10000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・場面の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    gas_seen = False
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        if state.phase is Phase.MAIN:
            working = gas_on(state)
            observed["main_gas_working" if working else ("main_gas_off_with_muk" if muk_in_play(state) else "main_no_muk")] += 1
            gas_seen = gas_seen or bool(working)
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                observed["rejected"] += 1
                if isinstance(command, UsePokemonPower):
                    kind = user_kind(state, command)
                    if error.code == "POWER_NOT_DECLARABLE" and kind == MUK:
                        observed["rejected_declare_gas"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED":
                        if not gas_on(state):
                            raise AssertionError(f"かがくへんかガスがはたらいていないのに POWER_SUPPRESSED: {command}")
                        observed[f"suppressed_{kind}"] += 1
                        if any(card_id(state, pk) == MUK for pk in state.players[state.current_player].in_play() if not blocked(pk)):
                            observed["suppressed_by_own_muk"] += 1
                        if any(card_id(state, pk) == MUK for pk in state.players[1 - state.current_player].in_play() if not blocked(pk)):
                            observed["suppressed_by_opponents_muk"] += 1
                        continue
                    if gas_on(state):
                        raise AssertionError(f"かがくへんかガスがはたらいているのに、ほかの理由（{error.code}）で拒否: {command}")
                    if error.code == "WOULD_KNOCK_OUT" and ("swap_ko_try", command) in turn_tried:
                        observed["rejected_swap_WOULD_KNOCK_OUT"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
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
        if isinstance(command, UsePokemonPower):
            if gas_on(state):
                raise AssertionError(f"かがくへんかガスがはたらいているのに特殊能力を受け付けた: {command}")
            kind = user_kind(state, command)
            observed[f"power_{kind}"] += 1
            if muk_in_play(state):
                observed["power_with_muk_in_play"] += 1  # ベトベトンはいるが、ねむり・マヒ・こんらん
            if gas_seen:
                observed["power_after_gas_gone"] += 1  # この対戦で前にかがくへんかガスがはたらいていた
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attack" and state.cards[e["pokemon"]].card_id in (GRIMER, MUK):
            counted[f"attack_{e['attack']}"] += 1
        elif kind == "special_condition" and state.cards[e["pokemon"]].card_id == MUK and not e.get("already"):
            counted[f"muk_{e['condition']}"] += 1
        elif kind == "special_conditions_removed" and state.cards[e["pokemon"]].card_id == MUK:
            counted[f"muk_condition_removed_{e['reason']}"] += 1
        elif kind == "knock_out":
            if state.cards[e["pokemon"]].card_id == MUK:
                counted["knock_out_muk"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 自然な対戦（SEEDS の 80 局）で数えた回数（v0.8）。手順・デッキ・乱数の使い方が変わると変わる。止まった 3 局は対戦準備の切り直しの
# 補償（v0.1 からの未解決）。MAIN の手を選ぶ時点でかがくへんかガスがはたらいていた 3,229 回・ベトベトンがいるのに消えていた 101 回・
# ベトベトンがいない 2,863 回。かがくへんかガスが消した特殊能力: エナジートランス 125・あまごい 32・ダメージスワップ 153（自分の
# ベトベトンで 206・相手のベトベトンで 145。両方がはたらいていれば両方に数える）。かがくへんかガスがはたらいたあとの対戦での使用 83 回
# （ベトベトンが場にいるがねむり・マヒ・こんらんのときの使用 24 回を含む）。かがくへんかガスの宣言の拒否 88 回。
EXPECTED_COUNTS = {
    "accepted": 7229, "attack_どくガス": 134, "attack_ねばりつく": 20, "attack_ヘドロこうげき": 218, "evolve_to_PMCG1-008": 61, "evolve_to_PMCG1-011": 39,
    "evolve_to_PMCG1-027": 48, "evolve_to_PMCG1-032": 32, "evolve_to_PMCG1-046": 133, "evolve_to_PMCG1-049": 79, "evolve_to_PMCG3-007": 118,
    "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "knock_out_muk": 31, "main_gas_off_with_muk": 101, "main_gas_working": 3229,
    "main_no_muk": 2863, "muk_condition_removed_evolve": 3, "muk_condition_removed_paralysis_end": 15, "muk_condition_removed_replaced": 1,
    "muk_condition_removed_retreat": 18, "muk_condition_removed_switch": 4, "muk_confusion": 26, "muk_paralysis": 16, "muk_poison": 12,
    "phase_game_over": 77, "phase_halted": 3, "power_PMCG1-011": 24, "power_PMCG1-032": 16, "power_PMCG1-049": 303,
    "power_after_gas_gone": 83, "power_with_muk_in_play": 24, "rejected": 844, "rejected_attack_POKEMON_PARALYZED": 47,
    "rejected_declare_gas": 88, "rejected_evolve2_EVOLVED_THIS_TURN": 113, "rejected_evolve_FIRST_TURN_EVOLUTION": 74,
    "rejected_evolve_PLAYED_THIS_TURN": 114, "rejected_power_POKEMON_PARALYZED": 1, "rejected_retreat_POKEMON_PARALYZED": 83,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 7, "rejected_swap_WOULD_KNOCK_OUT": 2,
    "stopped_attach_UNRESOLVED_ATTACH_AFTER_POWER_ATTACH": 5, "suppressed_PMCG1-011": 125, "suppressed_PMCG1-032": 32,
    "suppressed_PMCG1-049": 153, "suppressed_by_opponents_muk": 145, "suppressed_by_own_muk": 206, "take_prize": 365,
}

# 3 つの特殊能力がすべて消され、消えたあと（ベトベトンのこんらん・きぜつ）にまた使われる対戦
GOLDEN_SEED = 29
GOLDEN_SHAPE = (239, 76, Phase.GAME_OVER)
GOLDEN_DIGEST = "aff9c3e8681fd67832639cecb5feecedb05dc25f455e773f1c88f52976387046"


class FullGameWithMukTest(unittest.TestCase):
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
        """自然な対戦の中で、かがくへんかガスが 3 つの特殊能力を実際に消し、消えたあとに特殊能力がまた使われる（1 回も起こらない試験を成功と
        数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG3-007", "main_gas_working", "main_gas_off_with_muk", f"suppressed_{VENUSAUR}", f"suppressed_{BLASTOISE}",
                    f"suppressed_{ALAKAZAM}", "suppressed_by_own_muk", "suppressed_by_opponents_muk", "power_after_gas_gone",
                    "power_with_muk_in_play", "rejected_declare_gas", "knock_out_muk", "attack_どくガス", "attack_ねばりつく",
                    "attack_ヘドロこうげき", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（各時点のかがくへんかガスと特殊能力の宣言・特殊状態の組み立て直しを含む）・書き出しの監査（形式
        1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_no_randomness_for_the_gas(self):
        """かがくへんかガスは乱数を使わない: 対戦準備のあとの乱数はコインだけ（v0.7 と同じ確かめ方）。かがくへんかガスのログはない。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))
                self.assertFalse(any("gas" in e["kind"] or "suppress" in e["kind"] for e in state.log))

    def test_replay(self):
        for seed in SEEDS[:3]:
            state, commands, _ = self.games[seed]
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                replayed = apply_command(replayed, command)
            self.assertEqual(full(replayed), full(state))


class GoldenMukGameTest(unittest.TestCase):
    """ベトベトンに進化し、かがくへんかガスが 3 つの特殊能力を消す対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.8）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        for key in (f"suppressed_{VENUSAUR}", f"suppressed_{BLASTOISE}", f"suppressed_{ALAKAZAM}", "power_after_gas_gone", "power_with_muk_in_play"):
            self.assertGreater(observed[key], 0, (key, observed))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.10・v0.11・v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


def _power_while_muk_blocked(seed):
    """自然な対戦で、ベトベトンが場にいるが特殊状態（ねむり・マヒ・こんらん）で力が消えているときに受け付けた特殊能力の使用を探す。
    （対戦の状態, 宣言のログの位置, そのベトベトンの場のポケモンの番号）か None。"""
    state, commands, _ = play_game(seed, cure=seed % 3 != 0)
    replay = new_game(*decks(seed), seed)
    for command in commands:
        if isinstance(command, UsePokemonPower):
            blocked_muks = [pk.pokemon_id for p in replay.players for pk in p.in_play() if card_id(replay, pk) == MUK and blocked(pk)]
            if blocked_muks and not gas_on(replay):
                return state, len(replay.log), blocked_muks[0]
        replay = apply_command(replay, command)
    return None


class LogAuditGasTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、各時点の場（いちばん上のカード・ねむり・マヒ・こんらん）から求めたかがくへんかガスと、特殊能力の
    宣言の食い違いを見つけること（最後の状態だけから過去の使用を決めない。監査が何でも通すのではないことの確認）。"""

    @classmethod
    def setUpClass(cls):
        found = _power_while_muk_blocked(GOLDEN_SEED)
        assert found is not None
        cls.state, cls.index, cls.muk = found

    def broken(self, change_log):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        change_log(log)
        state.log = tuple(log)
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def test_original_passes(self):
        """元のログは通る（対戦の途中にかがくへんかガスがはたらいていた番も、特殊能力を使った番もある）。"""
        self.assertEqual(log_problems(self.state), [])
        self.assertEqual(self.state.log[self.index]["kind"], "pokemon_power")

    def test_detects_a_power_while_the_gas_works(self):
        """特殊能力を使う前に、ベトベトンを特殊状態にしたログを消すと、その時点でかがくへんかガスがはたらいていたことになり、特殊能力の使用を
        報告する（最後の状態との比較とは別に）。"""
        def drop_condition(log):
            last = max(i for i, e in enumerate(log[:self.index]) if e["kind"] == "special_condition" and e["pokemon_id"] == self.muk
                       and e["condition"] in ("sleep", "paralysis", "confusion") and not e.get("already"))
            del log[last]

        problems = self.broken(drop_condition)
        self.assertTrue(any("消されている特殊能力" in p for p in problems), problems)

    def test_detects_a_declared_gas(self):
        """かがくへんかガスの宣言（宣言しない特殊能力）を書き足すと報告する。"""
        def declare(log):
            event = dict(log[self.index])
            log.insert(self.index, {**event, "pokemon_id": self.muk, "power": "かがくへんかガス", "power_index": 0,
                                    "pokemon": next(e["to_card"] for e in log if e["kind"] == "evolve" and e["pokemon_id"] == self.muk)})

        problems = self.broken(declare)
        self.assertTrue(any("宣言しない特殊能力" in p for p in problems), problems)

    def test_detects_a_wrong_power_name(self):
        """宣言の特殊能力の名前・位置が、いちばん上のカードと合わなければ報告する。"""
        def rename(log):
            log[self.index] = {**log[self.index], "power": "かがくへんかガス"}

        problems = self.broken(rename)
        self.assertTrue(any("いちばん上のカードの特殊能力ではない" in p for p in problems), problems)

    def test_detects_a_condition_without_log(self):
        """状態とログから組み立てたねむり・マヒ・こんらんが違えば報告する（ログに特殊状態を書き足す）。"""
        in_play = [pk for p in self.state.players for pk in p.in_play() if pk.conditions.exclusive is None]
        target = in_play[0]

        def add_sleep(log):
            log.append({"kind": "special_condition", "turn": log[-1]["turn"], "player": 0, "pokemon": target.card,
                        "pokemon_id": target.pokemon_id, "condition": "sleep", "effect": "test"})

        problems = self.broken(add_sleep)
        self.assertTrue(any("ねむり・マヒ・こんらん" in p for p in problems), problems)


class GasStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py のベトベトンの組。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。"""

    def test_small_gas_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        scenarios = [s for s in stress.POWER_SCENARIOS if s.name.startswith("muk")]
        self.assertEqual(len(scenarios), 2)
        result = stress.run(scenarios, range(2), steps=300, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 4)
        for key in ("code:POWER_SUPPRESSED", "code:POWER_NOT_DECLARABLE", "observed:gas_working"):
            self.assertGreater(counts.get(key, 0), 0, (key, counts))
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


if __name__ == "__main__":
    unittest.main()
