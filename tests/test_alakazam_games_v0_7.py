"""ケーシィ → ユンゲラー → フーディン（v0.7）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ポケモンパワー「ダメージスワップ」（何度でも・バトル場とベンチのどちらのフーディンからでも・特殊状態で使えない・自分の場のポケモンの
ダメージカウンターを自分の場の別のポケモンへ・きぜつさせない）と、ねんりき・じこさいせい・ちょうねんりき・あやしいひかりを、v0.6
までのカード（フシギバナ・カメックスの系統・パウワウ → ジュゴン・コラッタ・ポケモンいれかえ・マサキ・きずぐすり・ディフェンダー）と
混ぜる。一方のデッキには、フシギバナ・カメックス・フーディンを同じデッキに入れる（3 つのパワーが同じ場にそろう番がある）。自然な
対戦の中で起こる出来事（進化・パワーの使用・1 つの番の中の複数回の使用・フーディンと移動元・移動先の場所・フーディン自身への移動・
進化したその番の使用・きぜつさせる移動の拒否・特殊状態による拒否・じこさいせいの決定・勝敗）の回数を数えて固定する
（docs/v0.7-verification.md）。盤面を直接作ったテストとは別に数える。

根拠のページは tests/test_damage_swap_v0_7.py・tests/test_alakazam_line_v0_7.py（p.149・p.151・p.153・p.307〜p.311・p.319〜p.323）。
手順は tests/test_blastoise_games_v0_6.py の ``policy_command`` に、ダメージスワップの使い方（下の ``damage_swap_command``）・
ユンゲラーのワザの選び方・じこさいせいの決定への答えを加えたもの（対戦相手の AI ではない）。

手順の決まりごと（ルールの制限ではない）:

- ダメージスワップは、ワザを使う前・番を終える前に、``choose_move`` の条件に合えば 1 個ずつ使う（1 つの番に ``MAX_SWAPS_PER_TURN`` 回
  まで）。
- 番の番号が 3 の倍数の番は、一度だけ、残り HP 10 のポケモンへ移すことを試す（きぜつさせる移動。エンジンは ``WOULD_KNOCK_OUT`` で
  拒否する。原典で禁止が確かめられている（S17）ので、拒否されたことを数える）。
- 場のフーディンがすべてねむり・マヒ・こんらんなら、その番に一度だけ試す（拒否されたことを数える）。
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
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    apply_command,
    can_pay_cost,
    check_invariants,
    new_game,
    state_to_dict,
)
from kyuura_engine.decisions import DISCARD_ENERGY
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    BILL,
    BLASTOISE,
    BULBASAUR,
    CARD_DATA_COMMIT_SINCE_V0_69,
    DEFENDER,
    DEWGONG,
    GRASS,
    IVYSAUR,
    KADABRA,
    POTION,
    PSYCHIC,
    RATTATA,
    SEEL,
    SQUIRTLE,
    SWITCH,
    VENUSAUR,
    WARTORTLE,
    WATER,
    coin_events,
    expand_decklist,
    with_card_data_commit_before_v0_69,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_blastoise_games_v0_6 import R13, blocked
from tests.test_blastoise_games_v0_6 import policy_command as blastoise_policy_command
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

ALAKAZAM_DECK_A = expand_decklist({
    ABRA: 4, KADABRA: 4, ALAKAZAM: 4, SEEL: 3, DEWGONG: 2, RATTATA: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 1, PSYCHIC: 24, WATER: 8,
})
# フシギバナ・カメックス・フーディンを同じデッキに（v0.5・v0.6・v0.7 のパワーが同じ場にそろう）
ALAKAZAM_DECK_B = expand_decklist({
    BULBASAUR: 3, IVYSAUR: 2, VENUSAUR: 2, SQUIRTLE: 3, WARTORTLE: 2, BLASTOISE: 2, ABRA: 3, KADABRA: 3, ALAKAZAM: 2, BILL: 4, POTION: 2,
    GRASS: 11, WATER: 11, PSYCHIC: 10,
})
SEEDS = tuple(range(80))
POWER_REJECTIONS = ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "POKEMON_CONFUSED")
MAX_SWAPS_PER_TURN = 10  # 手順の上限（ルールの制限ではない。「何度でも使える」）
LINE = (ABRA, KADABRA, ALAKAZAM)
POWER_POKEMON = (VENUSAUR, BLASTOISE, ALAKAZAM)


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (ALAKAZAM_DECK_A, ALAKAZAM_DECK_B) if seed % 2 == 0 else (ALAKAZAM_DECK_B, ALAKAZAM_DECK_A)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def remaining(state, pokemon):
    return state.card_def(pokemon.card).hp - pokemon.damage


def choose_move(state, mine, user):
    """移動元と移動先（決まった手順。どれにも当たらなければ None）:

    1. バトル場のポケモンの残り HP が 30 以下なら、バトル場から、残り HP がいちばん大きい（20 以上の）ベンチのポケモンへ（残り HP 10 まで
       のせることがある。p.153 の解説「ダメージカウンターをHPギリギリまでのせたら」）
    2. 番の番号が 5 の倍数の番は、ダメージのあるほかのポケモンから、使うフーディン自身へ（残り HP 30 以上のとき）
    3. 残り HP 20 以下のベンチのポケモンから、残り HP 40 以上のバトル場のポケモンへ
    4. 残り HP 20 以下のベンチのポケモンから、残り HP 40 以上のほかのベンチのポケモンへ
    """
    active, bench = mine[0], mine[1:]
    if active.damage and remaining(state, active) <= 30:
        targets = [pk for pk in bench if remaining(state, pk) >= 20]
        if targets:
            return active, max(targets, key=lambda pk: remaining(state, pk))
    if state.turn_number % 5 == 0 and remaining(state, user) >= 30:
        source = next((pk for pk in mine if pk is not user and pk.damage), None)
        if source is not None:
            return source, user
    weak = [pk for pk in bench if pk.damage and remaining(state, pk) <= 20]
    if weak and remaining(state, active) >= 40:
        return weak[0], active
    if weak:
        other = next((pk for pk in bench if pk is not weak[0] and remaining(state, pk) >= 40), None)
        if other is not None:
            return weak[0], other
    return None


def damage_swap_command(state, tried):
    """ダメージスワップの使い方（決まった手順）。フーディンが場にいて、この番の使用が上限より少ないとき、``choose_move`` の移動を使う。
    使うのは、特殊状態でない場のフーディンのうち、番の番号で決まる位置のもの（バトル場とベンチの両方にいれば、番ごとに交互）。
    番の番号が 3 の倍数の番は一度だけ、残り HP 10 のポケモンへ移すことを試す（きぜつさせる移動。拒否される）。どのフーディンも使えなければ、
    その番に一度だけ、使えないフーディンで試す（ねむり・マヒ・こんらんで拒否されることを、自然な対戦の中で確かめる）。"""
    player = state.current_player
    p = state.players[player]
    mine = p.in_play()
    users = [pk for pk in mine if card_id(state, pk) == ALAKAZAM]
    uses = sum(1 for e in state.log if e["kind"] == "move_damage_counter" and e["turn"] == state.turn_number)
    if not users or uses >= MAX_SWAPS_PER_TURN:
        return None
    usable = [pk for pk in users if not blocked(pk)]
    if not usable:
        if "swap_blocked" in tried:
            return None
        source = next((pk for pk in mine if pk.damage), None)
        target = next((pk for pk in mine if pk is not source), None)
        if source is None or target is None:
            return None
        tried.add("swap_blocked")
        return UsePokemonPower(player, users[0].pokemon_id, 0, None, source.pokemon_id, target.pokemon_id)
    user = usable[state.turn_number % len(usable)]
    if state.turn_number % 3 == 0 and "swap_ko_try" not in tried:
        full_target = next((pk for pk in mine if remaining(state, pk) == 10), None)
        source = next((pk for pk in mine if pk.damage and pk is not full_target), None)
        if full_target is not None and source is not None:
            command = UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, full_target.pokemon_id)
            tried.update({"swap_ko_try", ("swap_ko_try", command)})  # 拒否されるのは、この操作だけ（ほかの操作の拒否は誤り）
            return command
    move = choose_move(state, mine, user)
    if move is None:
        return None
    source, target = move
    return UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, target.pokemon_id)


def kadabra_attack(state, player):
    """ユンゲラーのワザ: ダメージが 30 以上で、じこさいせい（超超）を払えればじこさいせい、そうでなくちょうねんりきを払えればちょうねんりき、
    どちらでもなくダメージがあってじこさいせいを払えればじこさいせい。"""
    active = state.players[player].active
    recover, super_psy = (can_pay_cost(a.cost, state.energy_types(active)) for a in state.card_def(active.card).attacks)
    if recover and active.damage >= 30:
        return UseAttack(player, 0)
    if super_psy:
        return UseAttack(player, 1)
    if recover and active.damage:
        return UseAttack(player, 0)
    return None


def policy_command(state, *, janken_winner, cure, tried):
    """v0.6 の手順に、じこさいせいの決定への答え（番の番号で決まる位置のカード）・ダメージスワップ・ユンゲラーのワザの選び方を加える。"""
    if state.phase is Phase.DECISION and state.decision.kind == DISCARD_ENERGY:
        d = state.decision
        return ResolveDecision(d.player, d.id, (d.options[state.turn_number % len(d.options)],))
    command = blastoise_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)):
        return command
    power = damage_swap_command(state, tried)
    if power is not None:
        return power
    player = state.current_player
    if isinstance(command, UseAttack) and "attack" in tried:
        return EndTurn(player)  # この番のワザは拒否された（マヒなど）。もう一度は試さない（v0.3c の手順と同じ）
    if isinstance(command, UseAttack) and card_id(state, state.players[player].active) == KADABRA:
        return kadabra_attack(state, player) or command
    return command


def play_game(seed, *, cure=True, max_steps=8000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    all_three = set()
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            observed["turns_with_all_three_power_pokemon"] = len(all_three)
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
                    is_swap = card_id(state, state.find_pokemon(command.pokemon)[1]) == ALAKAZAM
                    if error.code == "WOULD_KNOCK_OUT" and is_swap and ("swap_ko_try", command) in turn_tried:
                        observed["rejected_swap_WOULD_KNOCK_OUT"] += 1
                        continue  # 一度だけ試す（turn_tried に swap_ko_try）。手順がきぜつしないと選んだ移動の拒否は誤りとして止める
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_{'swap' if is_swap else 'power'}_{error.code}"] += 1
                    continue  # 一度だけ試す（turn_tried に swap_blocked・rain_blocked・power_blocked）
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
        if p is not None and state.phase is Phase.MAIN and {card_id(state, pk) for pk in p.in_play()} >= set(POWER_POKEMON):
            all_three.add(state.turn_number)
        if isinstance(command, UsePokemonPower) and new.log[-1]["kind"] == "move_damage_counter":
            where = lambda pid: "active" if p.active.pokemon_id == pid else "bench"  # noqa: E731
            user = p.find_by_pokemon_id(command.pokemon)
            observed[f"swap_user_{where(command.pokemon)}"] += 1
            observed[f"swap_{where(command.source)}_to_{where(command.target)}"] += 1
            if command.target == command.pokemon:
                observed["swap_to_user"] += 1
            if command.source == command.pokemon:
                observed["swap_from_user"] += 1
            if user.evolved_turn == state.turn_number:
                observed["swap_by_alakazam_evolved_this_turn"] += 1
            if user.conditions.poison is not None:
                observed["swap_by_poisoned_alakazam"] += 1
            if new.log[-1]["from_total_damage"] == 0:
                observed["swap_source_emptied"] += 1
            if remaining(new, new.find_pokemon(command.target)[1]) == 10:
                observed["swap_target_filled_to_hp_minus_10"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    per_turn = Counter()
    powers_per_turn: dict[int, set] = {}
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            if state.cards[e["pokemon"]].card_id in LINE:
                counted[f"attack_{e['attack']}"] += 1
        elif kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "move_damage_counter":
            counted["move_damage_counter"] += 1
            per_turn[e["turn"]] += 1
            powers_per_turn.setdefault(e["turn"], set()).add("swap")
        elif kind == "power_attach_energy":
            powers_per_turn.setdefault(e["turn"], set()).add("rain")
        elif kind == "move_energy":
            powers_per_turn.setdefault(e["turn"], set()).add("trans")
        elif kind == "discard_energy":
            counted["recover_discard_energy"] += 1
        elif kind == "remove_all_damage_counters":
            counted["recover_counters_removed"] += e["counters"]
        elif kind == "special_condition" and e.get("effect") == "PMCG1-043#0":
            counted["psyshock_paralysis"] += 1
        elif kind == "special_condition" and e.get("effect") == "PMCG1-049#0":
            counted["confuse_ray_confusion"] += 1
        elif kind == "knock_out":
            if state.cards[e["pokemon"]].card_id == ALAKAZAM:
                counted["knock_out_alakazam"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    if per_turn:
        counted["turns_with_damage_swap"] += len(per_turn)
        counted["turns_with_two_or_more_damage_swaps"] += sum(1 for n in per_turn.values() if n >= 2)
        counted["max_damage_swaps_in_a_turn"] = max(per_turn.values())
    counted["turns_with_two_kinds_of_power"] += sum(1 for kinds_ in powers_per_turn.values() if len(kinds_) >= 2 and "swap" in kinds_)
    counted["turns_with_three_kinds_of_power"] += sum(1 for kinds_ in powers_per_turn.values() if len(kinds_) == 3)
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithAlakazamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            events = count_events(state)
            maximum = events.pop("max_damage_swaps_in_a_turn", 0)
            counted["max_damage_swaps_in_a_turn"] = max(counted["max_damage_swaps_in_a_turn"], maximum)
            counted.update(events)
            counted.update(observed)
        return counted

    def test_counts(self):
        """自然な対戦の中で、ダメージスワップ・ケーシィの系統のワザが実際に使われる（1 回も使われない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG1-046", "evolve_to_PMCG1-049", "move_damage_counter", "turns_with_two_or_more_damage_swaps",
                    "swap_user_active", "swap_user_bench", "swap_active_to_bench", "swap_bench_to_active", "swap_bench_to_bench",
                    "swap_to_user", "swap_by_alakazam_evolved_this_turn", "swap_source_emptied", "swap_target_filled_to_hp_minus_10",
                    "rejected_swap_WOULD_KNOCK_OUT", "attack_ねんりき", "attack_じこさいせい", "attack_ちょうねんりき", "attack_あやしいひかり",
                    "recover_discard_energy", "turns_with_all_three_power_pokemon", "turns_with_two_kinds_of_power", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertGreaterEqual(counted["max_damage_swaps_in_a_turn"], 2)
        # 1 回の使用で 1 個: 受け付けた使用の回数 = ダメージカウンターの移動のログの数
        self.assertEqual(counted["swap_user_active"] + counted["swap_user_bench"], counted["move_damage_counter"])
        # じこさいせいは、トラッシュととりのぞく処理が 1 回ずつ
        self.assertEqual(counted["attack_じこさいせい"], counted["recover_discard_energy"] + self.confused_recover_attempts())
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def confused_recover_attempts(self):
        """こんらんの「うら」で処理しなかった、じこさいせいの回数（ログの attack のすぐあとが confusion_check の「うら」）。"""
        count = 0
        for state, _, _ in self.games.values():
            log = [dict(e) for e in state.log]
            for i, e in enumerate(log):
                if e["kind"] == "attack" and e["attack"] == "じこさいせい":
                    later = log[i + 1:i + 3]
                    if any(x["kind"] == "confusion_check" and x.get("result") == "tails" for x in later):
                        count += 1
        return count

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（ダメージカウンターの移動・じこさいせいの組み立て直しを含む）・書き出しの監査（形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_damage_swap_keeps_total_damage_and_never_knocks_out(self):
        """どのダメージスワップも、宣言のすぐあとに 1 個の移動で、移動先のダメージは HP より小さい（きぜつがない）。乱数はコインだけ
        （ダメージスワップ・じこさいせいは乱数を使わない）。ダメージスワップを使った番は、そのあとも同じプレイヤーの番が続く。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                log = [dict(e) for e in state.log]
                for index, e in enumerate(log):
                    if e["kind"] != "move_damage_counter":
                        continue
                    self.assertEqual((log[index - 1]["kind"], log[index - 1]["pokemon_id"], e["count"]), ("pokemon_power", e["pokemon_id"], 1))
                    nxt = log[index + 1] if index + 1 < len(log) else None
                    self.assertTrue(nxt is None or nxt["kind"] != "knock_out")
                    later = [x for x in log[index + 1:] if x["turn"] == e["turn"]]
                    self.assertTrue(any(x["kind"] == "turn_end" for x in later) or state.phase in TERMINAL)
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


def _find_game(predicate):
    for seed in SEEDS:
        state, _, _ = play_game(seed, cure=seed % 3 != 0)
        found = predicate(state)
        if found is not None:
            return state, found
    raise AssertionError("条件に合う対戦が見つからない")


class LogAuditDamageSwapTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、ダメージカウンターの移動のログ・状態の壊れを見つけること（監査が何でも通すのではないことの確認）。"""

    @classmethod
    def setUpClass(cls):
        def last_swap(state):
            in_play = {pk.pokemon_id: pk for p in state.players for pk in p.in_play()}
            uses = [i for i, e in enumerate(state.log) if e["kind"] == "move_damage_counter" and e["from_pokemon_id"] in in_play
                    and e["to_pokemon_id"] in in_play and len(state.players[e["player"]].in_play()) >= 3
                    and state.players[1 - e["player"]].in_play() and state.log[i - 1]["kind"] == "pokemon_power"]
            return uses[-1] if uses else None
        cls.state, cls.index = _find_game(last_swap)

    def broken(self, change_log=None, change_state=None):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        if change_log:
            change_log(log)
        state.log = tuple(log)
        if change_state:
            change_state(state)
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])

    def test_detects_broken_damage_swap(self):
        use = dict(self.state.log[self.index])
        player = self.state.players[use["player"]]
        others = [pk.pokemon_id for pk in player.in_play() if pk.pokemon_id not in (use["from_pokemon_id"], use["to_pokemon_id"])]
        opponent_pokemon = self.state.players[1 - use["player"]].in_play()[0]  # 対戦が終わった状態なので、バトル場がいないこともある

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

        def extra_declaration(log):
            # 処理のない宣言を 1 つ書き足す（状態は変わらないので、宣言と処理の対応の確認だけが見つける。変異 35）
            log.insert(self.index - 1, dict(log[self.index - 1]))

        def reversed_order(log):
            log[self.index - 1], log[self.index] = log[self.index], log[self.index - 1]

        def moved_in_state_only(state):
            p = state.players[use["player"]]
            source = p.find_by_pokemon_id(use["to_pokemon_id"])
            target = p.find_by_pokemon_id(use["from_pokemon_id"])
            if source.damage >= 10:
                source.damage -= 10
                target.damage += 10
            else:
                source.damage += 10

        def wrong_power(log):
            log[self.index] = {**log[self.index], "power": "PMCG1-011@power0"}

        def after_attack(log):
            attack = next(i for i, e in enumerate(log) if e["kind"] == "attack" and e["turn"] == use["turn"]) \
                if any(e["kind"] == "attack" and e["turn"] == use["turn"] for e in log) else None
            if attack is None:  # この番にワザがなければ、番の終わりのあとに移す（番の終わりのあとの特殊能力）
                attack = next(i for i, e in enumerate(log) if e["kind"] == "turn_end" and e["turn"] == use["turn"])
            pair = [log[self.index - 1], log[self.index]]
            del log[self.index - 1:self.index + 1]
            attack -= 2 if attack > self.index else 0
            log[attack + 1:attack + 1] = pair

        cases = [
            ("移動のログを消す", drop, None),
            ("移動元を変える", edit(from_pokemon_id=others[0]) if others else edit(from_pokemon_id=use["to_pokemon_id"]), None),
            ("移動先を変える", edit(to_pokemon_id=others[0]) if others else edit(to_pokemon_id=use["from_pokemon_id"]), None),
            ("向きを逆にする", edit(from_pokemon_id=use["to_pokemon_id"], to_pokemon_id=use["from_pokemon_id"]), None),
            ("数を 2 にする", edit(count=2), None),
            ("移動元をない番号にする", edit(from_pokemon_id=999), None),
            ("移動先を相手のポケモンにする", edit(to_pokemon_id=opponent_pokemon.pokemon_id), None),
            ("移動元を相手のポケモンにする", edit(from_pokemon_id=opponent_pokemon.pokemon_id), None),
            ("同じポケモンにする", edit(to_pokemon_id=use["from_pokemon_id"]), None),
            ("移動のあとのダメージを変える", edit(to_total_damage=use["to_total_damage"] + 10), None),
            ("移動のログを 2 回", duplicate, None),
            ("宣言のログを消す", without_declaration, None),
            ("宣言と移動の順番を逆にする", reversed_order, None),
            ("処理のない宣言を書き足す", extra_declaration, None),
            ("ほかのパワー（エナジートランス）の移動にする", wrong_power, None),
            ("ワザ・番の終わりのあとに移す", after_attack, None),
            ("状態だけ動かす（ログなし）", None, moved_in_state_only),
        ]
        for name, change_log, change_state in cases:
            with self.subTest(change=name):
                self.assertTrue(self.broken(change_log, change_state))

    def test_detects_a_knock_out_by_moving(self):
        """ログの最後に、残り HP がなくなるまで移したことにする宣言と移動を書き足すと、「きぜつするダメージになった」と報告する（状態との
        食い違いとは別に）。"""
        use = dict(self.state.log[self.index])
        p = self.state.players[use["player"]]
        target = p.find_by_pokemon_id(use["to_pokemon_id"])
        source = p.find_by_pokemon_id(use["from_pokemon_id"])
        hp = self.state.card_def(target.card).hp
        steps = (hp - target.damage) // 10

        def forge(log):
            turn = log[-1]["turn"]
            s, t = source.damage + 10 * steps, target.damage
            for _ in range(steps):
                s, t = s - 10, t + 10
                log.append({**log[self.index - 1], "turn": turn})
                log.append({**log[self.index], "turn": turn, "from_pokemon_id": source.pokemon_id, "to_pokemon_id": target.pokemon_id,
                            "from_total_damage": s, "to_total_damage": t})
        problems = self.broken(forge)
        self.assertTrue(any("きぜつするダメージ" in problem for problem in problems), problems)


class LogAuditRecoverTest(unittest.TestCase):
    """じこさいせいのログ（``discard_energy``・``remove_all_damage_counters``）の壊れを見つけること。"""

    @classmethod
    def setUpClass(cls):
        def last_recover(state):
            in_play = {pk.pokemon_id for p in state.players for pk in p.in_play()}
            uses = [i for i, e in enumerate(state.log) if e["kind"] == "discard_energy" and e["pokemon_id"] in in_play
                    and state.log[i + 1]["kind"] == "remove_all_damage_counters" and state.log[i + 1]["counters"] > 0]
            return uses[-1] if uses else None
        cls.state, cls.index = _find_game(last_recover)

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
        self.assertEqual(log_problems(self.state), [])

    def test_detects_broken_recover(self):
        discard = dict(self.state.log[self.index])
        other = next(u for u in self.state.cards if u != discard["energy"] and self.state.cards[u].owner == discard["player"]
                     and self.state.card_def(u).is_basic_energy)

        def edit(index, **fields):
            def change(log):
                log[index] = {**log[index], **fields}
            return change

        def drop(index):
            def change(log):
                log.pop(index)
            return change

        def duplicate(index):
            def change(log):
                log.insert(index + 1, dict(log[index]))
            return change

        cases = [
            ("トラッシュのログを消す", drop(self.index)),
            ("とりのぞくログを消す", drop(self.index + 1)),
            ("トラッシュしたカードを変える", edit(self.index, energy=other)),
            ("とりのぞいた量を変える", edit(self.index + 1, amount=discard_amount(self.state, self.index) - 10)),
            ("トラッシュのログを 2 回", duplicate(self.index)),
        ]
        for name, change in cases:
            with self.subTest(change=name):
                self.assertTrue(self.broken(change))


def discard_amount(state, index):
    return state.log[index + 1]["amount"]


class DamageSwapStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py のフーディンの組。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。
    ダメージスワップの使用（できそうなもの・わざと不正なもの）を混ぜても、内部の誤り・拒否で変わる状態・ログと書き出しの問題がない。"""

    def test_small_damage_swap_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        scenarios = [s for s in stress.POWER_SCENARIOS if s.name.startswith("alakazam")]
        self.assertEqual(len(scenarios), 2)
        result = stress.run(scenarios, range(2), steps=300, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 4)
        self.assertGreater(counts.get("accepted:damage_swap", 0), 0, counts)
        self.assertGreater(sum(v for k, v in counts.items() if k in ("code:SAME_POKEMON", "code:NO_DAMAGE_COUNTERS", "code:WOULD_KNOCK_OUT",
                                                                       "code:TARGET_NOT_YOURS", "code:SOURCE_NOT_YOURS",
                                                                       "code:POWER_CHOICE_NOT_USED", "code:POWER_CHOICE_MISSING")), 0, counts)
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


class GoldenAlakazamGameTest(unittest.TestCase):
    """フーディンに 2 進化し、ダメージスワップを使う対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.7）。"""

    def test_seed(self):
        state, commands, _ = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evolve_to_PMCG1-049", "move_damage_counter"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        # v0.69: 写しの元を上げた（7d3f4ca）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT_SINCE_V0_69)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.8・v0.9・v0.10・v0.11・v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


# 自然な対戦（SEEDS の 80 局）で数えた回数（v0.7）。手順・デッキ・乱数の使い方が変わると変わる。止まった 9 局は対戦準備の
# 切り直しの補償（v0.1 からの未解決）。受け付けた操作 7,025 回、ダメージスワップの使用 1,000 回（バトル場のフーディンから
# 578・ベンチから 422、バトル場 → ベンチ 619・ベンチ → バトル場 362・ベンチ → ベンチ 19、フーディン自身へ 476・
# フーディン自身から 426、進化したその番のフーディンで 67・どく状態のフーディンで 14、移動元が 0 になった 100・
# 移動先が残り HP 10 になった 93、1 つの番の中の 2 回以上が 137 番・最大 10 回）、きぜつさせる移動の拒否
# 20 回、特殊状態による拒否 18 回、拒否の合計 520 回（ほかのパワー・ワザ・にげる・進化・R13 を含む）。
# フシギバナ・カメックス・フーディンが同じ場にそろった番 37
EXPECTED_COUNTS = {
    "accepted": 7025, "attack_あやしいひかり": 204, "attack_じこさいせい": 37, "attack_ちょうねんりき": 34, "attack_ねんりき": 140, "confuse_ray_confusion": 58,
    "evolve_to_PMCG1-008": 50, "evolve_to_PMCG1-011": 26, "evolve_to_PMCG1-027": 40, "evolve_to_PMCG1-030": 42, "evolve_to_PMCG1-032": 29,
    "evolve_to_PMCG1-046": 156, "evolve_to_PMCG1-049": 100, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 9, "knock_out_alakazam": 39,
    "max_damage_swaps_in_a_turn": 10, "move_damage_counter": 1000, "phase_game_over": 71, "phase_halted": 9, "psyshock_paralysis": 68,
    "recover_counters_removed": 19, "recover_discard_energy": 37, "rejected": 520, "rejected_attack_POKEMON_PARALYZED": 67,
    "rejected_evolve2_EVOLVED_THIS_TURN": 107, "rejected_evolve_FIRST_TURN_EVOLUTION": 72, "rejected_evolve_PLAYED_THIS_TURN": 93,
    "rejected_power_POKEMON_CONFUSED": 9, "rejected_power_POKEMON_PARALYZED": 5, "rejected_retreat_POKEMON_PARALYZED": 103,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 16, "rejected_swap_POKEMON_CONFUSED": 1, "rejected_swap_POKEMON_PARALYZED": 17,
    "rejected_swap_WOULD_KNOCK_OUT": 20, "stopped_attach_UNRESOLVED_ATTACH_AFTER_POWER_ATTACH": 10, "swap_active_to_bench": 619,
    "swap_bench_to_active": 362, "swap_bench_to_bench": 19, "swap_by_alakazam_evolved_this_turn": 67, "swap_by_poisoned_alakazam": 14,
    "swap_from_user": 426, "swap_source_emptied": 100, "swap_target_filled_to_hp_minus_10": 93, "swap_to_user": 476,
    "swap_user_active": 578, "swap_user_bench": 422, "take_prize": 307, "turns_with_all_three_power_pokemon": 37,
    "turns_with_damage_swap": 173, "turns_with_two_kinds_of_power": 14, "turns_with_two_or_more_damage_swaps": 137,
}

GOLDEN_SEED = 46  # ダメージスワップ 33 回（ベンチのフーディンから 23・フーディン自身へ 18）、じこさいせい 5 回、あやしいひかり 2 回
GOLDEN_SHAPE = (170, 44, Phase.GAME_OVER)
GOLDEN_DIGEST = "c77289bf7584d52b035f7b02e0e73a5a01c5d3b0babe6fba64f6dc85c53fd966"


if __name__ == "__main__":
    unittest.main()
