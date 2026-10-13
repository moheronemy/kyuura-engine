"""ゼニガメ → カメール → カメックス（v0.6）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ポケモンパワー「あまごい」（何度でも・バトル場とベンチのどちらのカメックスからでも・特殊状態で使えない・手札の「水」エネルギーを
自分の「水」ポケモンへ）と、あわ・からにこもる・かみつく・ハイドロポンプを、v0.5 までのカード（パウワウ → ジュゴン・ヒトデマン・
ピカチュウ・ロコン・パラス・キャタピー・ポケモンいれかえ・マサキ・きずぐすり・プラスパワー・ディフェンダー）と混ぜる。自然な対戦の
中で起こる出来事（進化・パワーの使用・1 つの番の中の複数回の使用・カメックスとつける先の場所・通常の操作との組み合わせ・特殊状態に
よる拒否・R13 の停止・つけたエネルギーのトラッシュ・ハイドロポンプの追加のダメージ・勝敗）の回数を数えて固定する
（docs/v0.6-verification.md）。盤面を直接作ったテストとは別に数える。

根拠のページは tests/test_rain_dance_v0_6.py・tests/test_squirtle_line_v0_6.py（p.87・p.88・p.90・p.307・p.309〜p.311・
p.319〜p.323）。手順は tests/test_bulbasaur_games_v0_5.py の ``policy_command`` に、あまごいの使い方（下の ``rain_dance_command``）を
加えたもの（対戦相手の AI ではない）。

手順の決まりごと（ルールの制限ではない）:

- あまごいは、ふつうはワザを使う前・番を終える前に使う（そのときには、手順はもう手札からつける通常の操作を済ませている。R12）。
- ``RAIN_FIRST`` の番（番の番号で決まる）は、通常の操作より先にあまごいを使い、そのあとの通常の操作を 1 回だけ試す。原典で決められない
  ので、エンジンは ``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`` で止める（R13）。止まった回数を数え、その番は通常の操作をしない。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import EnergyType
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    BILL, BLASTOISE, CATERPIE, DEFENDER, DEWGONG, FIRE, LIGHTNING, PARAS, PIKACHU, PLUSPOWER, POTION, SEEL, SQUIRTLE, STARYU, SWITCH,
    VULPIX, WARTORTLE, WATER, best_affordable_attack, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_bulbasaur_games_v0_5 import need
from tests.test_bulbasaur_games_v0_5 import policy_command as bulbasaur_policy_command
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

BLASTOISE_DECK_A = expand_decklist({
    SQUIRTLE: 4, WARTORTLE: 4, BLASTOISE: 4, SEEL: 3, DEWGONG: 2, STARYU: 2, SWITCH: 2, POTION: 2, BILL: 4, PLUSPOWER: 2, DEFENDER: 1,
    WATER: 30,
})
BLASTOISE_DECK_B = expand_decklist({
    SQUIRTLE: 3, WARTORTLE: 3, BLASTOISE: 2, PIKACHU: 3, VULPIX: 3, PARAS: 3, CATERPIE: 2, BILL: 3, POTION: 2, DEFENDER: 2, WATER: 20,
    LIGHTNING: 8, FIRE: 6,
})
SEEDS = tuple(range(80))
POWER_REJECTIONS = ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "POKEMON_CONFUSED")
R13 = "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH"
MAX_RAIN_DANCE_PER_TURN = 8  # 手順の上限（ルールの制限ではない。「何度でも使える」）
LINE = (SQUIRTLE, WARTORTLE, BLASTOISE)


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (BLASTOISE_DECK_A, BLASTOISE_DECK_B) if seed % 2 == 0 else (BLASTOISE_DECK_B, BLASTOISE_DECK_A)


def rain_first(turn_number):
    """通常の操作より先にあまごいを使う番（手順の決まりごと）。"""
    return turn_number % 4 in (1, 2)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def is_water(state, pokemon):
    return state.card_def(pokemon.card).pokemon_type is EnergyType.WATER


def waters(state, pokemon):
    return [u for u in pokemon.energy if state.card_def(u).provides is EnergyType.WATER]


def blocked(pokemon):
    c = pokemon.conditions
    return c.asleep or c.paralyzed or c.confused


def rain_dance_command(state, tried):
    """あまごいの使い方（決まった手順）。カメックスが場にいて、手札に「水」エネルギーがあり、この番の使用が上限より少ないとき、
    つける先を次の順に選ぶ:

    1. バトル場の「水」ポケモンが、いちばん重いワザを払えない
    2. バトル場のカメックスの「水」が 5 個より少ない（ハイドロポンプの追加のダメージ。p.88 の解説「水エネルギー5個まで」）
    3. ベンチのゼニガメの系統のポケモンのうち、いちばん重いワザを払えない最初のもの
    4. ベンチのほかの「水」ポケモン（パウワウ・ジュゴン・ヒトデマン）のうち、いちばん重いワザを払えない最初のもの

    使うのは、場のカメックスのうち特殊状態でない最初のもの（バトル場が先）。どれも使えなければ、その番に一度だけ、使えないカメックス
    で試す（ねむり・マヒ・こんらんで拒否されることを、自然な対戦の中で確かめる）。"""
    player = state.current_player
    p = state.players[player]
    users = [pk for pk in p.in_play() if card_id(state, pk) == BLASTOISE]
    hand = [u for u in p.hand if state.card_def(u).is_basic_energy and state.card_def(u).provides is EnergyType.WATER]
    uses = sum(1 for e in state.log if e["kind"] == "power_attach_energy" and e["turn"] == state.turn_number)
    if not users or not hand or uses >= MAX_RAIN_DANCE_PER_TURN:
        return None
    active = p.active
    target = None
    if is_water(state, active) and need(state, active):
        target = active
    elif card_id(state, active) == BLASTOISE and len(waters(state, active)) < 5:
        target = active
    else:
        target = next((pk for pk in p.bench if card_id(state, pk) in LINE and need(state, pk)), None)
        if target is None:
            target = next((pk for pk in p.bench if is_water(state, pk) and need(state, pk)), None)
    if target is None:
        return None
    usable = [pk for pk in users if not blocked(pk)]
    if usable:
        user = usable[0]
    elif "rain_blocked" not in tried:
        tried.add("rain_blocked")
        user = users[0]
    else:
        return None
    return UsePokemonPower(player, user.pokemon_id, 0, hand[0], None, target.pokemon_id)


def policy_command(state, *, janken_winner, cure, tried):
    """v0.5 の手順に、あまごいを加える。ふつうはワザを使う前・番を終える前に ``rain_dance_command`` の条件に合えば使う。``rain_first`` の
    番は、通常の操作の前に使い、そのあと通常の操作を 1 回だけ試す（R13 で止まる）。止まったら、その番は通常の操作をせず、ワザか番の
    終わりへ進む。"""
    command = bulbasaur_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    if isinstance(command, AttachEnergy):
        if "attach_blocked" in tried:
            index = best_affordable_attack(state, player)
            command = EndTurn(player) if index is None else UseAttack(player, index)
        elif rain_first(state.turn_number) and "rain_first" not in tried:
            power = rain_dance_command(state, tried)
            if power is not None:
                tried.add("rain_first")
                return power
            return command
        else:
            return command
    if not isinstance(command, (UseAttack, EndTurn)):
        return command
    power = rain_dance_command(state, tried)
    return command if power is None else power


def play_game(seed, *, cure=True, max_steps=8000):
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
                observed["rejected"] += 1
                if isinstance(command, UsePokemonPower):
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue  # 一度だけ試す（turn_tried に rain_blocked・power_blocked）
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
        p = state.players[state.current_player] if state.current_player in (0, 1) else None
        if isinstance(command, UsePokemonPower) and new.log[-1]["kind"] == "power_attach_energy":
            where = lambda pid: "active" if p.active.pokemon_id == pid else "bench"  # noqa: E731
            user = p.find_by_pokemon_id(command.pokemon)
            observed[f"rain_user_{where(command.pokemon)}"] += 1
            observed[f"rain_target_{where(command.target)}"] += 1
            if command.target == command.pokemon:
                observed["rain_target_is_user"] += 1
            if state.energy_attachments_this_turn:
                observed["rain_after_attaching_from_hand"] += 1
            if user.evolved_turn == state.turn_number:
                observed["rain_by_blastoise_evolved_this_turn"] += 1
            if user.conditions.poison is not None:
                observed["rain_by_poisoned_blastoise"] += 1
        if isinstance(command, UseAttack) and p is not None and card_id(state, p.active) == BLASTOISE:
            extra = min(max(0, len(waters(state, p.active)) - 3), 2)
            observed[f"hydro_pump_extra_{extra}"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    rain_energy = set()
    per_turn = Counter()
    attach_turns = set()
    last_attack = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            last_attack = state.cards[e["pokemon"]].card_id
            if last_attack in LINE:
                counted[f"attack_{e['attack']}"] += 1
        elif kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attach_energy":
            attach_turns.add(e["turn"])
        elif kind == "power_attach_energy":
            counted["power_attach_energy"] += 1
            per_turn[e["turn"]] += 1
            rain_energy.add(e["energy"])
        elif kind == "special_condition" and e.get("effect") == "PMCG1-023#0":
            counted["bubble_paralysis"] += 1
        elif kind == "persistent_effect_added":
            counted["withdraw_prevent_damage"] += 1
        elif kind == "knock_out":
            if state.cards[e["pokemon"]].card_id == BLASTOISE:
                counted["knock_out_blastoise"] += 1
            if set(e["discarded_energy"]) & rain_energy:
                counted["knock_out_with_rain_dance_energy"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    if per_turn:
        counted["turns_with_rain_dance"] += len(per_turn)
        counted["turns_with_two_or_more_rain_dances"] += sum(1 for n in per_turn.values() if n >= 2)
        counted["turns_with_rain_dance_and_attach_from_hand"] += len(set(per_turn) & attach_turns)
        counted["max_rain_dances_in_a_turn"] = max(per_turn.values())
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithBlastoiseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            events = count_events(state)
            maximum = events.pop("max_rain_dances_in_a_turn", 0)
            counted["max_rain_dances_in_a_turn"] = max(counted["max_rain_dances_in_a_turn"], maximum)
            counted.update(events)
            counted.update(observed)
        return counted

    def test_counts(self):
        """自然な対戦の中で、あまごい・ゼニガメの系統のワザが実際に使われる（1 回も使われない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG1-027", "evolve_to_PMCG1-032", "power_attach_energy", "turns_with_two_or_more_rain_dances",
                    "turns_with_rain_dance_and_attach_from_hand", "rain_user_active", "rain_user_bench", "rain_target_active",
                    "rain_target_bench", "rain_target_is_user", "rain_after_attaching_from_hand", "rain_by_blastoise_evolved_this_turn",
                    f"stopped_attach_{R13}", "attack_ハイドロポンプ", "attack_あわ", "attack_かみつく", "hydro_pump_extra_0",
                    "hydro_pump_extra_2", "knock_out_blastoise", "knock_out_with_rain_dance_energy", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertGreaterEqual(counted["max_rain_dances_in_a_turn"], 2)
        # 1 回の使用で 1 枚: 受け付けた使用の回数 = 手札からつけたログの数
        self.assertEqual(counted["rain_user_active"] + counted["rain_user_bench"], counted["power_attach_energy"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（手札とあまごいの組み立て直しを含む）・書き出しの監査（形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_rain_dance_does_not_end_the_turn_or_use_randomness(self):
        """あまごいを使った番は、そのあとも同じプレイヤーの番が続く。対戦準備のあとの乱数はコインだけ（あまごいは乱数を使わない）。
        通常の操作は 1 番に 1 回まで、あまごいのあと（通常の操作をまだしていない番）にはない（R13 は止める）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                log = [dict(e) for e in state.log]
                for index, e in enumerate(log):
                    if e["kind"] != "power_attach_energy":
                        continue
                    later = [x for x in log[index + 1:] if x["turn"] == e["turn"]]
                    self.assertTrue(any(x["kind"] == "turn_end" for x in later) or state.phase in TERMINAL)
                    earlier = [x for x in log[:index] if x["turn"] == e["turn"]]
                    if not any(x["kind"] == "attach_energy" for x in earlier):
                        self.assertFalse(any(x["kind"] == "attach_energy" for x in later))
                attaches = Counter(e["turn"] for e in log if e["kind"] == "attach_energy")
                self.assertLessEqual(max(attaches.values(), default=0), 1)
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


class LogAuditRainDanceTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、手札からつけたログ・手札・状態の壊れを見つけること（監査が何でも通すのではないことの確認）。"""

    @classmethod
    def setUpClass(cls):
        for seed in SEEDS:
            state, _, _ = play_game(seed, cure=seed % 3 != 0)
            in_play = {pk.pokemon_id: pk for p in state.players for pk in p.in_play()}
            uses = [i for i, e in enumerate(state.log) if e["kind"] == "power_attach_energy" and e["to_pokemon_id"] in in_play
                    and e["energy"] in in_play[e["to_pokemon_id"]].energy and state.players[e["player"]].hand
                    and len(state.players[e["player"]].in_play()) >= 2 and state.players[1 - e["player"]].active is not None
                    and any(state.card_def(pk.card).pokemon_type is not EnergyType.WATER for pk in state.players[e["player"]].in_play())]
            if uses:
                cls.state, cls.index = state, uses[-1]
                return
        raise AssertionError("最後まで場に残る、あまごいでつけたエネルギーのある対戦が見つからない")

    def broken(self, change_log=None, change_state=None):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        if change_log:
            change_log(log)
        state.log = tuple(log)
        if change_state:
            change_state(state)
        return log_problems(state)

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])

    def test_detects_broken_rain_dance(self):
        use = dict(self.state.log[self.index])
        player = self.state.players[use["player"]]
        others = [pk.pokemon_id for pk in player.in_play() if pk.pokemon_id != use["to_pokemon_id"]]
        not_water = next(pk.pokemon_id for pk in player.in_play() if self.state.card_def(pk.card).pokemon_type is not EnergyType.WATER)
        in_hand = player.hand[0]
        opponent = self.state.players[1 - use["player"]]
        opponent_card = (opponent.hand or opponent.deck)[0]

        def edit(**fields):
            def change(log):
                log[self.index] = {**log[self.index], **fields}
            return change

        def drop(log):
            log.pop(self.index)

        def duplicate(log):
            log.insert(self.index + 1, dict(log[self.index]))

        def without_declaration(log):
            log.pop(self.index - 1)

        def as_normal_attach(log):
            log[self.index] = {"kind": "attach_energy", "turn": use["turn"], "player": use["player"], "energy": use["energy"],
                               "target": next(pk.card for pk in player.in_play() if pk.pokemon_id == use["to_pokemon_id"])}

        def attached_without_log(state):
            p = state.players[use["player"]]
            uid = p.hand.pop(0)
            p.active.energy.append(uid)

        def back_to_hand(state):
            p = state.players[use["player"]]
            pokemon = p.find_by_pokemon_id(use["to_pokemon_id"])
            pokemon.energy.remove(use["energy"])
            p.hand.append(use["energy"])

        def normal_attach_after(log):
            # あまごいのすぐあとに、同じ番の通常の操作を書き足す（つける先はあまごいを使ったポケモン。R13 はエンジンが止めるので、
            # そのようなログはない。同じ番にもう通常の操作があれば 2 回目）
            log.insert(self.index + 1, {"kind": "attach_energy", "turn": use["turn"], "player": use["player"], "energy": use["energy"],
                                        "target": use["pokemon"]})
            log[self.index] = {**log[self.index], "energy": in_hand}

        cases = [
            ("手札からつけたログを消す", drop, None),
            ("つける先を変える", edit(to_pokemon_id=others[0]), None),
            ("つける先を相手のポケモンにする", edit(to_pokemon_id=opponent.active.pokemon_id), None),
            ("つける先を水でないポケモンにする", edit(to_pokemon_id=not_water), None),
            ("エネルギーの uid を手札にあるカードにする", edit(energy=in_hand), None),
            ("エネルギーの uid を相手のカードにする", edit(energy=opponent_card), None),
            ("手札からつけたログを 2 回", duplicate, None),
            ("宣言のログを消す", without_declaration, None),
            ("通常の操作のログにすりかえる", as_normal_attach, None),
            ("状態だけ動かす（ログなし）", None, attached_without_log),
            ("状態だけ手札にもどす", None, back_to_hand),
        ]
        for name, change_log, change_state in cases:
            with self.subTest(change=name):
                try:
                    problems = self.broken(change_log, change_state)
                except (KeyError, ValueError, StopIteration, AttributeError):
                    problems = ["組み立て直せない"]
                self.assertTrue(problems)
        # あまごいのあとの通常の操作は、R13（または 1 番に 1 回）の問題として報告する
        problems = self.broken(normal_attach_after)
        self.assertTrue(any("R13" in p or "通常の操作が" in p for p in problems), problems)


class RainDanceStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py のカメックスの組。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。
    あまごいの使用（できそうなもの・わざと不正なもの）を混ぜても、内部の誤り・拒否で変わる状態・ログと書き出しの問題がない。"""

    def test_small_rain_dance_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        scenarios = [s for s in stress.POWER_SCENARIOS if s.name.startswith("blastoise")]
        self.assertEqual(len(scenarios), 2)
        result = stress.run(scenarios, range(2), steps=250, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 4)
        self.assertGreater(counts.get("accepted:rain_dance", 0), 0, counts)
        self.assertGreater(sum(v for k, v in counts.items() if k in ("code:CARD_NOT_IN_HAND", "code:WRONG_POKEMON_TYPE", "code:TARGET_NOT_YOURS",
                                                                       "code:POWER_CHOICE_NOT_USED", "code:POWER_CHOICE_MISSING")), 0, counts)
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


class GoldenBlastoiseGameTest(unittest.TestCase):
    """カメックスに 2 進化し、あまごいを使う対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.6）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evolve_to_PMCG1-032", "power_attach_energy"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.7")  # v0.7 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


# 自然な対戦（SEEDS の 80 局）で数えた回数（v0.6）。手順・デッキ・乱数の使い方が変わると変わる。止まった 3 局は対戦準備の
# 切り直しの補償（v0.1 からの未解決）。受け付けた操作 4,872 回、あまごいの使用 187 回（バトル場のカメックスから 141・ベンチから 46、
# 1 つの番の中の 2 回以上が 37 番・最大 5 回、通常の操作のあとの使用 105 回・通常の操作と同じ番 65 番、進化したその番のカメックスで
# 82 回）、R13 で止めた通常の操作 17 回、拒否 306 回（R13 の 17 回を含む）、あまごいでつけたエネルギーがきぜつでトラッシュされた 21 回
EXPECTED_COUNTS = {
    "accepted": 4872, "attack_あわ": 165, "attack_かみつく": 65, "attack_からにこもる": 46, "attack_ハイドロポンプ": 186, "bubble_paralysis": 74,
    "evolve_to_PMCG1-027": 128, "evolve_to_PMCG1-030": 38, "evolve_to_PMCG1-032": 79,
    "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "hydro_pump_extra_0": 39, "hydro_pump_extra_1": 27, "hydro_pump_extra_2": 120,
    "knock_out_blastoise": 26, "knock_out_with_rain_dance_energy": 21, "max_rain_dances_in_a_turn": 5, "phase_game_over": 77,
    "phase_halted": 3, "power_attach_energy": 187, "rain_after_attaching_from_hand": 105,
    "rain_by_blastoise_evolved_this_turn": 82, "rain_target_active": 86, "rain_target_bench": 101, "rain_target_is_user": 116,
    "rain_user_active": 141, "rain_user_bench": 46, "rejected": 306, "rejected_attack_POKEMON_PARALYZED": 55,
    "rejected_evolve2_EVOLVED_THIS_TURN": 58, "rejected_evolve_FIRST_TURN_EVOLUTION": 57, "rejected_evolve_PLAYED_THIS_TURN": 46,
    "rejected_retreat_POKEMON_PARALYZED": 73, "stopped_attach_UNRESOLVED_ATTACH_AFTER_POWER_ATTACH": 17, "take_prize": 339,
    "turns_with_rain_dance": 136, "turns_with_rain_dance_and_attach_from_hand": 65, "turns_with_two_or_more_rain_dances": 37,
    "withdraw_prevent_damage": 23,
}

GOLDEN_SEED = 18  # あまごい 10 回（ベンチのカメックスから 5・ベンチへ 4）、つけたエネルギーのトラッシュ 3 回、ハイドロポンプ 10 回
GOLDEN_SHAPE = (139, 43, Phase.GAME_OVER)
GOLDEN_DIGEST = "e04cff010bceb38d0b7aa82ed622c15a297c16b7b3dfdc1ccc01df7485a2efe9"


if __name__ == "__main__":
    unittest.main()
