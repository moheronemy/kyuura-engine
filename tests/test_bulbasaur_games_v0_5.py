"""フシギダネ → フシギソウ → フシギバナ（v0.5）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

ポケモンパワー「エナジートランス」（何度でも・バトル場とベンチのどちらのフシギバナからでも・特殊状態で使えない）と、やどりぎのタネ・
どくのこな（コインなし）・つるのむち・ソーラービームを、v0.4d までのカード（ビードル → コクーン・ロコン・パラス・キャタピー・ガーディ・
プラスパワー・ディフェンダー・ポケモンいれかえ・マサキ・きずぐすり）と混ぜる。自然な対戦の中で起こる出来事（進化・パワーの使用・
1 つの番の中の複数回の使用・移動元と移動先の場所・特殊状態による拒否・どく状態での使用・つけかえたエネルギーのトラッシュ・
ワザの結果・勝敗）の回数を数えて固定する（docs/v0.5-verification.md）。盤面を直接作ったテストとは別に数える。

根拠のページは tests/test_pokemon_powers_v0_5.py・tests/test_venusaur_v0_5.py・tests/test_bulbasaur_line_v0_5.py
（p.13・p.14・p.16・p.309〜p.311・p.319〜p.323）。手順は tests/test_butterfree_games_v0_4d.py の ``policy_command`` に、
エナジートランスの使い方（下の ``energy_trans_command``）とフシギソウのワザの選び方を加えたもの（対戦相手の AI ではない）。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    EndTurn, EvolvePokemon, IllegalActionError, Phase, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.cards import EnergyType, can_pay_cost
from kyuura_engine.rng import copy_rng, rng_fingerprint

from tests.helpers import (
    BILL, BULBASAUR, CATERPIE, DEFENDER, FIRE, GRASS, GROWLITHE, IVYSAUR, KAKUNA, PARAS, PLUSPOWER, POTION, SWITCH, VENUSAUR,
    VULPIX, WEEDLE, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_butterfree_games_v0_4d import policy_command as butterfree_policy_command
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

VENUSAUR_DECK_A = expand_decklist({
    BULBASAUR: 4, IVYSAUR: 4, VENUSAUR: 3, WEEDLE: 3, KAKUNA: 2, SWITCH: 2, POTION: 2, BILL: 3, PLUSPOWER: 2, DEFENDER: 1, GRASS: 34,
})
VENUSAUR_DECK_B = expand_decklist({
    BULBASAUR: 4, IVYSAUR: 3, VENUSAUR: 2, VULPIX: 3, PARAS: 3, CATERPIE: 3, GROWLITHE: 2, BILL: 3, POTION: 2, DEFENDER: 2,
    GRASS: 27, FIRE: 6,
})
SEEDS = tuple(range(48))
POWER_REJECTIONS = ("POKEMON_ASLEEP", "POKEMON_PARALYZED", "POKEMON_CONFUSED")
MAX_POWER_USES_PER_TURN = 12  # 手順の上限（ルールの制限ではない。「何度でも使える」）


def full(state):
    return state_to_dict(state, format_version=8)


def decks(seed):
    return (VENUSAUR_DECK_A, VENUSAUR_DECK_B) if seed % 2 == 0 else (VENUSAUR_DECK_B, VENUSAUR_DECK_A)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def grass(state, pokemon):
    return [u for u in pokemon.energy if state.card_def(u).provides is EnergyType.GRASS]


def need(state, pokemon):
    """そのポケモンのいちばん重いワザ（必要なエネルギーがいちばん多いもの）を払うのに足りないか。"""
    attacks = [a for a in state.card_def(pokemon.card).attacks if a.supported]
    if not attacks:
        return False
    heaviest = max(attacks, key=lambda a: (len(a.cost), a.index))
    return not can_pay_cost(heaviest.cost, state.energy_types(pokemon))


def excess(state, pokemon):
    """いちばん重いワザを払ったうえで余る「草」エネルギー（1 枚移しても払えるなら、その 1 枚）。"""
    attacks = [a for a in state.card_def(pokemon.card).attacks if a.supported]
    heaviest = max(attacks, key=lambda a: (len(a.cost), a.index))
    for uid in grass(state, pokemon):
        rest = [state.card_def(u).provides for u in pokemon.energy if u != uid]
        if can_pay_cost(heaviest.cost, rest):
            return uid
    return None


def energy_trans_command(state, tried):
    """エナジートランスの使い方（決まった手順）。フシギバナが場にいて、この番の使用が上限より少ないとき:

    1. 集める: バトル場のポケモンがいちばん重いワザを払えなければ、ベンチのポケモン（「草」エネルギーのいちばん多いもの）の「草」を
       バトル場へ（払えるまで・ベンチの「草」がなくなるまで何度でも）
    2. 守る: 1 で動かせず、番を終えるとき（ワザを使わないとき）、バトル場のポケモンの残りの HP が 30 以下なら、その「草」をすべて
       ベンチのフシギソウ・フシギバナ（いなければベンチの先頭）へ。一度始めたら、その番は 1・3 をしない
    3. 分ける: バトル場のポケモンに、いちばん重いワザを払っても余る「草」があり、ベンチに払えないフシギダネの系統のポケモンがいれば、1 枚へ
    4. ベンチどうし: 3 で動かせず、ベンチのポケモンに余る「草」があり、ほかのベンチに払えないフシギダネの系統のポケモンがいれば、1 枚へ

    使うのは、場のフシギバナのうち特殊状態でない最初のもの（バトル場が先）。どれも使えなければ、その番に一度だけ、使えない
    フシギバナで試す（ねむり・マヒ・こんらんで拒否されることを、自然な対戦の中で確かめる）。"""
    player = state.current_player
    p = state.players[player]
    users = [pk for pk in p.in_play() if card_id(state, pk) == VENUSAUR]
    uses = sum(1 for e in state.log if e["kind"] == "move_energy" and e["turn"] == state.turn_number)
    if not users or uses >= MAX_POWER_USES_PER_TURN:
        return None
    usable = [pk for pk in users if not (pk.conditions.asleep or pk.conditions.paralyzed or pk.conditions.confused)]
    active = p.active
    move = None
    if "power_rescue" not in tried and need(state, active):
        sources = sorted((pk for pk in p.bench if grass(state, pk)), key=lambda pk: -len(grass(state, pk)))
        if sources:
            move = (grass(state, sources[0])[0], sources[0], active)
    remaining = state.card_def(active.card).hp - active.damage
    if move is None and "ending" in tried and p.bench and grass(state, active) and remaining <= 30:
        tried.add("power_rescue")
        line = [pk for pk in p.bench if card_id(state, pk) in (IVYSAUR, VENUSAUR)]
        move = (grass(state, active)[0], active, (line or p.bench)[0])
    if move is None and "power_rescue" not in tried:
        spare = excess(state, active)
        targets = [pk for pk in p.bench if card_id(state, pk) in (BULBASAUR, IVYSAUR, VENUSAUR) and need(state, pk)]
        if spare is not None and targets:
            move = (spare, active, targets[0])
    if move is None and "power_rescue" not in tried:
        for source in p.bench:
            spare = excess(state, source)
            targets = [pk for pk in p.bench if pk is not source and card_id(state, pk) in (BULBASAUR, IVYSAUR, VENUSAUR) and need(state, pk)]
            if spare is not None and targets:
                move = (spare, source, targets[0])
                break
    if move is None:
        return None
    energy, source, target = move
    if usable:
        user = usable[0]
    elif "power_blocked" not in tried:
        tried.add("power_blocked")
        user = users[0]
    else:
        return None
    return UsePokemonPower(player, user.pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id)


def policy_command(state, *, janken_winner, cure, tried):
    """v0.4d の手順（1 進化・2 進化・「かたまる」・スピアー・バタフリー）に、エナジートランスとフシギソウのワザの選び方を加える。
    ワザを使う前・番を終える前に、``energy_trans_command`` の条件に合えばエナジートランスを使う。フシギソウは、相手の対戦ポケモンが
    どく状態でなく、どくのこな（草 3）を払えればどくのこな、そうでなければつるのむち。"""
    command = butterfree_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)):
        return command
    if isinstance(command, EndTurn):
        tried.add("ending")
    power = energy_trans_command(state, tried)
    if power is not None:
        return power
    player = state.current_player
    active = state.players[player].active
    if isinstance(command, UseAttack) and card_id(state, active) == IVYSAUR:
        whip, powder = (can_pay_cost(a.cost, state.energy_types(active)) for a in state.card_def(active.card).attacks)
        if powder and state.players[1 - player].active.conditions.poison is None:
            return UseAttack(player, 1)
        if whip:
            return UseAttack(player, 0)
    return command


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
                if isinstance(command, UsePokemonPower):
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue  # 一度だけ試す（turn_tried に power_blocked）
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
        if isinstance(command, UsePokemonPower):
            p = state.players[command.player]
            where = lambda pid: "active" if p.active.pokemon_id == pid else "bench"  # noqa: E731
            observed[f"power_user_{where(command.pokemon)}"] += 1
            observed[f"power_move_{where(command.source)}_to_{where(command.target)}"] += 1
            if command.source == command.pokemon or command.target == command.pokemon:
                observed["power_user_is_source_or_target"] += 1
            if p.active.conditions.poison is not None and p.active.pokemon_id == command.pokemon:
                observed["power_used_by_poisoned_venusaur"] += 1
            if state.energy_attachments_this_turn:
                observed["power_after_attaching_from_hand"] += 1
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    last_attack = None
    moved_energy = set()
    per_turn = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            last_attack = (state.cards[e["pokemon"]].card_id, e["attack"])
            if last_attack[0] in (BULBASAUR, IVYSAUR, VENUSAUR):
                counted[f"attack_{e['attack']}"] += 1
        elif kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "move_energy":
            counted["move_energy"] += 1
            per_turn[e["turn"]] += 1
            if e["energy"] in moved_energy:
                counted["move_energy_again"] += 1
            moved_energy.add(e["energy"])
        elif kind == "drain_heal" and last_attack == (BULBASAUR, "やどりぎのタネ"):
            counted["leech_seed_heal" if e["counters"] else "leech_seed_heal_zero"] += 1
        elif kind == "special_condition" and e["effect"] == "PMCG1-008#1":
            counted["poisonpowder_poison_already" if e.get("already") else "poisonpowder_poison"] += 1
        elif kind == "knock_out":
            stack = e.get("evolution_stack", ())
            name = state.cards[e["pokemon"]].card_id
            if name == VENUSAUR:
                counted["knock_out_venusaur"] += 1
            if set(e["discarded_energy"]) & moved_energy:
                counted["knock_out_with_moved_energy"] += 1
            counted[f"knock_out_{len(stack) + 1}_cards"] += 1
        elif kind == "take_prize":
            counted["take_prize"] += 1
    if per_turn:
        counted["turns_with_power"] += len(per_turn)
        counted["turns_with_two_or_more_moves"] += sum(1 for n in per_turn.values() if n >= 2)
        counted["max_moves_in_a_turn"] = max(per_turn.values())
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


class FullGameWithVenusaurTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def test_counts(self):
        """自然な対戦の中で、エナジートランス・フシギダネの系統のワザが実際に使われる（1 回も使われない試験を成功と数えない）。"""
        counted = Counter()
        for state, _, observed in self.games.values():
            events = count_events(state)
            maximum = events.pop("max_moves_in_a_turn", 0)
            counted["max_moves_in_a_turn"] = max(counted["max_moves_in_a_turn"], maximum)
            counted.update(events)
            counted.update(observed)
        for key in ("evolve_to_PMCG1-008", "evolve_to_PMCG1-011", "move_energy", "move_energy_again", "turns_with_two_or_more_moves",
                    "power_user_active", "power_user_bench", "power_user_is_source_or_target", "power_move_bench_to_active",
                    "power_move_active_to_bench", "power_move_bench_to_bench", "power_after_attaching_from_hand",
                    "power_used_by_poisoned_venusaur", "rejected_power_POKEMON_ASLEEP", "rejected_power_POKEMON_PARALYZED",
                    "rejected_power_POKEMON_CONFUSED", "attack_やどりぎのタネ", "attack_どくのこな", "attack_つるのムチ",
                    "attack_ソーラービーム", "leech_seed_heal", "leech_seed_heal_zero", "poisonpowder_poison", "knock_out_venusaur",
                    "knock_out_with_moved_energy", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertGreaterEqual(counted["max_moves_in_a_turn"], 2)
        # 1 回の使用で 1 枚: 受け付けた使用の回数 = エネルギーの移動のログの数
        self.assertEqual(counted["power_user_active"] + counted["power_user_bench"], counted["move_energy"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（エネルギーの移動の組み立て直しを含む）・書き出しの監査（形式 1〜8）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_power_uses_do_not_end_the_turn_or_use_randomness(self):
        """エナジートランスを使った番は、そのあとも同じプレイヤーの番が続く（同じ番に、そのあとワザ・番の終わりがある）。対戦準備の
        あとの乱数はコインだけ（エナジートランスは乱数を使わない）。手札からつけた回数はつけかえで増えない（1 番に 1 回まで）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                log = [dict(e) for e in state.log]
                for index, e in enumerate(log):
                    if e["kind"] != "move_energy":
                        continue
                    later = [x for x in log[index + 1:] if x["turn"] == e["turn"]]
                    self.assertTrue(any(x["kind"] == "turn_end" for x in later) or state.phase in TERMINAL)
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


class LogAuditMoveEnergyTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、エネルギーの移動のログ・状態の壊れを見つけること（監査が何でも通すのではないことの確認）。"""

    @classmethod
    def setUpClass(cls):
        for seed in SEEDS:
            state, _, _ = play_game(seed, cure=seed % 3 != 0)
            in_play = {pk.pokemon_id: pk for p in state.players for pk in p.in_play()}
            moves = [i for i, e in enumerate(state.log) if e["kind"] == "move_energy" and e["to_pokemon_id"] in in_play
                     and e["from_pokemon_id"] in in_play and e["energy"] in in_play[e["to_pokemon_id"]].energy
                     and len(state.players[e["player"]].in_play()) >= 3 and state.players[1 - e["player"]].active is not None]
            if moves:
                cls.state, cls.index = state, moves[-1]
                return
        raise AssertionError("最後まで場に残る移動のある対戦が見つからない")

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

    def test_detects_broken_moves(self):
        move = dict(self.state.log[self.index])
        player = self.state.players[move["player"]]
        others = [pk.pokemon_id for pk in player.in_play() if pk.pokemon_id not in (move["from_pokemon_id"], move["to_pokemon_id"])]
        other_energy = next(u for pk in player.in_play() for u in pk.energy if u != move["energy"])
        opponent = self.state.players[1 - move["player"]].active.pokemon_id

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

        def moved_without_log(state):
            pokemon = {pk.pokemon_id: pk for pk in state.players[move["player"]].in_play()}
            uid = pokemon[move["to_pokemon_id"]].energy.pop()
            pokemon[others[0]].energy.append(uid)

        def logged_without_state(log):
            target = others[0]
            log.insert(self.index + 1, {**move, "kind": "pokemon_power", "power": "エナジートランス", "power_index": 0})
            log.insert(self.index + 2, {**move, "from_pokemon_id": move["to_pokemon_id"], "to_pokemon_id": target})

        for name, change_log, change_state in (
            ("移動のログを消す", drop, None),
            ("移動先を変える", edit(to_pokemon_id=others[0]), None),
            ("移動先を相手のポケモンにする", edit(to_pokemon_id=opponent), None),
            ("エネルギーの uid を変える", edit(energy=other_energy), None),
            ("移動のログを 2 回", duplicate, None),
            ("宣言のログを消す", without_declaration, None),
            ("状態だけ動かす（ログなし）", None, moved_without_log),
            ("ログだけ（状態は動いていない）", logged_without_state, None),
        ):
            with self.subTest(change=name):
                try:
                    problems = self.broken(change_log, change_state)
                except (KeyError, ValueError, StopIteration):
                    problems = ["組み立て直せない"]
                self.assertTrue(problems)


class PowerStressSmokeTest(unittest.TestCase):
    """大規模なストレス実行（tools/stress_engine.py の ``POWER_SCENARIOS``。段階 C）と同じ処理を、小さく 1 回だけ走らせる（段階 B）。
    エナジートランスの使用（できそうなもの・わざと不正なもの）を混ぜても、内部の誤り・拒否で変わる状態・ログと書き出しの問題がない。"""

    def test_small_power_stress_run(self):
        import importlib.util
        import pathlib

        path = pathlib.Path(__file__).resolve().parent.parent / "tools" / "stress_engine.py"
        spec = importlib.util.spec_from_file_location("stress_engine", path)
        stress = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stress)
        result = stress.run(stress.POWER_SCENARIOS, range(2), steps=200, illegal_rate=0.25, serialize_every=10)
        self.assertEqual(result["failures"], [])
        counts = result["counts"]
        self.assertEqual(counts["games"], 2 * len(stress.POWER_SCENARIOS))
        self.assertGreater(counts.get("accepted:UsePokemonPower", 0), 0, counts)
        self.assertGreater(sum(v for k, v in counts.items() if k in ("code:SAME_POKEMON", "code:TARGET_NOT_YOURS", "code:NO_POKEMON_POWER",
                                                                       "code:POWER_CHOICE_MISSING")), 0, counts)
        self.assertEqual(counts.get("internal_error", 0) + counts.get("internal_state_integrity", 0), 0)


class GoldenVenusaurGameTest(unittest.TestCase):
    """フシギバナに 2 進化し、エナジートランスを使う対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.5）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        counted = count_events(state)
        for key in ("evolve_to_PMCG1-011", "move_energy"):
            self.assertGreater(counted[key], 0, (key, counted))
        data = full(state)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.8")  # v0.6・v0.7・v0.8 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


# 自然な対戦（SEEDS の 48 局）で数えた回数（v0.5）。手順・デッキ・乱数の使い方が変わると変わる。止まった 3 局は対戦準備の
# 切り直しの補償（v0.1 からの未解決）。エナジートランスの使用 383 回（1 つの番の中の 2 回以上が 84 番・最大 12 回（手順の上限）・
# バトル場から 92 回・ベンチから 291 回）、特殊状態のフシギバナでの拒否 8 回（ねむり 5・マヒ 2・こんらん 1）、どく状態のフシギバナ
# での使用 3 回、つけかえたエネルギーがきぜつでトラッシュされた 13 回
EXPECTED_COUNTS = {
    "attack_つるのムチ": 10, "attack_どくのこな": 46, "attack_やどりぎのタネ": 69, "attack_ソーラービーム": 102, "evolve_to_PMCG1-008": 109,
    "evolve_to_PMCG1-009": 33, "evolve_to_PMCG1-011": 70, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "knock_out_1_cards": 182,
    "knock_out_2_cards": 34, "knock_out_3_cards": 17, "knock_out_venusaur": 17, "knock_out_with_moved_energy": 13, "leech_seed_heal": 36,
    "leech_seed_heal_zero": 22, "max_moves_in_a_turn": 12, "move_energy": 383, "move_energy_again": 120, "phase_game_over": 45,
    "phase_halted": 3, "poisonpowder_poison": 40, "power_after_attaching_from_hand": 324, "power_move_active_to_bench": 269,
    "power_move_bench_to_active": 93, "power_move_bench_to_bench": 21, "power_used_by_poisoned_venusaur": 3, "power_user_active": 92,
    "power_user_bench": 291, "power_user_is_source_or_target": 312, "rejected_attack_POKEMON_ASLEEP": 40,
    "rejected_attack_POKEMON_PARALYZED": 52, "rejected_evolve2_EVOLVED_THIS_TURN": 42, "rejected_evolve_FIRST_TURN_EVOLUTION": 32,
    "rejected_evolve_PLAYED_THIS_TURN": 36, "rejected_power_POKEMON_ASLEEP": 5, "rejected_power_POKEMON_CONFUSED": 1,
    "rejected_power_POKEMON_PARALYZED": 2, "rejected_retreat_POKEMON_ASLEEP": 48, "rejected_retreat_POKEMON_PARALYZED": 60,
    "rejected_retreat_RETREAT_ALREADY_FAILED": 5, "take_prize": 233, "turns_with_power": 180, "turns_with_two_or_more_moves": 84,
}

GOLDEN_SEED = 22  # エナジートランス 18 回（バトル場へ 8・ベンチへ 10）、つけかえたエネルギーのトラッシュを含む
GOLDEN_SHAPE = (87, 22, Phase.GAME_OVER)
GOLDEN_DIGEST = "d302d873a47f40bdeeb5a7eae854be2f3bb59e3c624504f65fecee3ae48e30fb"


if __name__ == "__main__":
    unittest.main()
