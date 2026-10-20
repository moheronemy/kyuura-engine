"""v0.18c: ナツメのヤドン（PMCG6-044。p.155）の「ぐうたらこうげき」。docs/kernel-reuse-v0.18c.md。

- 最新の説明「ダメージを与えた後、自分を「ねむり」状態にする。」（p.155）は、R団のカビゴンの「たおれこむ」（p.245。v0.17b）と同じ文面。既存の実装の型
  ``DamageAndSelfSleep``（要素 ``Damage(OPP)`` → ``Status(SLEEP, target=SELF, after_damage="damage")``）で登録し、新しい要素・型・分岐・効果の定義を
  加えない。``engine.py``・``resolution/kernel.py``・``resolution/v013_checks.py``・``resolution/contract.py`` は変えない。
- ダメージを与えなかったとき（Z23。kyuura の UQ-EFFECT-AFTER-NO-DAMAGE）は決めずに止める。超のワザなので、抵抗力 超 −30 の相手（コラッタ・ミニリュウ・
  サカキのニャース・R団のカビゴン）で最終ダメージが 0 になる場合（Z23-b）が、たおれこむ（無色）と違って実際のカードで起こる。

根拠のページ: p.155（最新の説明・解説）・p.245（同じ文面の「たおれこむ」）・p.309・p.315・p.319〜p.322。kyuura の記録 id: PMCG6-044・
UQ-EFFECT-AFTER-NO-DAMAGE（cases に「ぐうたらこうげき」）・CR-COLLAPSE-ORDER・CR-COLLAPSE-SELF-KO・CR-COLLAPSE-AFTER-KO-DEFENDER・
CR-COLLAPSE-SPECIAL-CONDITIONS（たおれこむの記録。同じ文面への当てはめ）（NEO-2000-OFFICIAL-RULES）。
"""

from __future__ import annotations

import hashlib
import json
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    IllegalActionError, Phase, UnsupportedError, UseAttack, apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.conditions import SLEEP
from kyuura_engine.damage import calculate_confusion_damage
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import PreventDamage
from tests.helpers import (
    CARD_DATA_COMMIT_SINCE_V0_69,
    with_card_data_commit_before_v0_69,
    ATTACK_TYPES_SINCE_V0_17, BILL, CATERPIE, DEFENDER, DODUO, DRATINI, GASTLY, GIOVANNIS_MEOWTH, H, HAUNTER, MACHOP, METAPOD,
    PLUSPOWER, PONYTA, POTION, PSYCHIC, RATTATA, ROCKETS_MOLTRES, ROCKETS_SNORLAX, SABRINAS_SLOWPOKE, SWITCH, T, apply_kernel,
    build_test_state, coin_events, expand_decklist, with_coin_results,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_confusion_games import TERMINAL
from tests.test_dark_wartortle_games_v0_13 import WARTORTLE_DECK
from tests.test_haunter_games_v0_9 import card_id
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_moltres_games_v0_12 import MOLTRES_DECK_A, MOLTRES_DECK_B
from tests.test_rocket_snorlax_v0_17b import SNORLAX_DECK, restless_working
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.v017_games import full, play_game

TURN = 7  # プレイヤー 0 の番
LAZY = E.AttackKey(SABRINAS_SLOWPOKE, 0)
TUMBLE = E.AttackKey(ROCKETS_SNORLAX, 0)
NO_DAMAGE = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
PSYCHIC_RESISTANT = (RATTATA, DRATINI, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX)  # 抵抗力 超 −30


def slowpoke(**extra):
    return {"card": SABRINAS_SLOWPOKE, "energy": [PSYCHIC, PSYCHIC], **extra}


def board(mine, theirs, *, turn=TURN, **kwargs):
    return build_test_state([{"active": mine, "bench": [RATTATA]}, {"active": theirs, "bench": [RATTATA]}], turn_number=turn, **kwargs)


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def kinds(state, since):
    return [e["kind"] for e in state.log[since:] if e["kind"] not in ("turn_end", "pokemon_check", "turn_start", "draw")]


class RegistrationTest(unittest.TestCase):
    def test_card_registration_and_reuse(self):
        """照合の記録（p.155）と登録。実装の型・要素の並びはたおれこむと同じで、新しい型・要素・効果の定義はない。v0.13 の約束のアダプタ
        （contract）でも、v0.13 の止める関数で確かめる型（v013_checks.VERIFIED）でもない。"""
        pool = load_card_pool()
        definition = pool.get(SABRINAS_SLOWPOKE)
        self.assertTrue(definition.supported and pool.is_playable(SABRINAS_SLOWPOKE) and definition.is_basic_pokemon)
        self.assertEqual((definition.hp, definition.pokemon_type.value, definition.weakness.value, definition.resistance, definition.retreat_cost),
                         (50, "psychic", "psychic", None, 1))
        self.assertEqual(definition.powers, ())
        entry = E.DEFAULT_EFFECTS.attack_entry(LAZY.card_id, LAZY.attack_index)
        tumble = E.DEFAULT_EFFECTS.attack_entry(TUMBLE.card_id, TUMBLE.attack_index)
        record = read_verification()["cards"][SABRINAS_SLOWPOKE]
        self.assertEqual(record["status"], "一致")
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         ("ぐうたらこうげき", definition.attacks[0].text_ja, record["latest_description_ja"], "P43 p.155"))
        self.assertEqual(entry.play_text_ja, tumble.play_text_ja)  # 同じ最新の説明（p.155・p.245）
        self.assertIs(type(entry.effect), type(tumble.effect))
        self.assertEqual(entry.effect, tumble.effect)
        self.assertIn(type(entry.effect), ATTACK_TYPES_SINCE_V0_17)
        self.assertNotIn(type(entry.effect), v013_checks.VERIFIED)
        program = programs.compile_attack(entry.effect)
        self.assertEqual(program, programs.compile_attack(tumble.effect))
        self.assertEqual(program, (programs.Damage(programs.OPP, programs.Printed()),
                                   programs.Status(SLEEP, target=programs.SELF, after_damage="damage")))
        self.assertFalse(contract.is_contract(contract.program_for(entry.effect)))
        self.assertIs(E.DamageAndSelfSleep.resolve, E.AttackEffect.resolve)

    def test_only_one_new_registration(self):
        """v0.17 から変わったのは、ナツメのヤドンの登録 1 つだけ（ワザの型の数・要素の並びの対応表は変わらない）。"""
        self.assertEqual([k for k in E.DEFAULT_EFFECTS.attack_keys() if k.card_id == SABRINAS_SLOWPOKE], [LAZY])
        types = {type(E.DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) for k in E.DEFAULT_EFFECTS.attack_keys()}
        self.assertEqual(sorted(t.__name__ for t in types - set(v013_checks.VERIFIED)), sorted(t.__name__ for t in ATTACK_TYPES_SINCE_V0_17))


class LazyAttackTest(unittest.TestCase):
    """ぐうたらこうげき。プレイヤー 0 のナツメのヤドンがワザを使う。"""

    def test_damage_then_self_sleep(self):
        """相手に 30 → 自分をねむり（要素の順番。kyuura の CR-COLLAPSE-ORDER の当てはめ）。そのあとのポケモンチェックで持ち主がねむりのコインを投げる。"""
        state = board(slowpoke(), PONYTA)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "special_condition"])
        self.assertEqual(events(new, len(state.log), "damage")[0]["amount"], 30)
        condition = events(new, len(state.log), "special_condition")[0]
        self.assertEqual((condition["player"], condition["condition"], condition["effect"]), (0, "sleep", str(LAZY)))
        self.assertTrue(new.players[0].active.conditions.asleep)
        self.assertEqual(events(new, len(state.log), "sleep_check")[0]["player"], 0)

    def test_weakness_and_defender_neighbours(self):
        """弱点（ワンリキーは超の弱点。60）・ディフェンダー（30 − 20 = 10）でもダメージを与えたので、自分はねむりになる（Z23 で止まらない）。"""
        for target, amount in ((MACHOP, 60), ({"card": PONYTA, "trainers": [(DEFENDER, TURN)]}, 10),
                               ({"card": MACHOP, "trainers": [(DEFENDER, TURN)]}, 40)):
            with self.subTest(target=target):
                state = board(slowpoke(), target)
                new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
                self.assertEqual(events(new, len(state.log), "damage")[0]["amount"], amount)
                self.assertTrue(new.players[0].active.conditions.asleep)

    def test_knocking_out_the_defender_still_sleeps(self):
        """相手をきぜつさせても（ダメージを与えた）、自分はねむりになる（kyuura の CR-COLLAPSE-AFTER-KO-DEFENDER の当てはめ）。"""
        state = board(slowpoke(), {"card": PONYTA, "damage": 10})
        new = apply_command(state, UseAttack(0, 0))
        order = kinds(new, len(state.log))
        self.assertLess(order.index("special_condition"), order.index("knock_out"))

    def test_self_knocked_out_by_fire_wall_is_not_put_to_sleep(self):
        """ほのおのかべ（v0.12）の 10 で自分が HP 以上になったら、ねむりにしない（効果の対象のポケモンの処理がない。kyuura の CR-COLLAPSE-SELF-KO の
        当てはめ。p.309・p.89）。R団のファイヤーはきぜつしないので W24 で止まらない。"""
        state = board(slowpoke(damage=40), {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1})
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "retaliation"])
        self.assertEqual(events(new, len(state.log), "special_condition"), [])
        self.assertIn("knock_out", kinds(new, len(state.log)))

    def test_conditions_of_slowpoke(self):
        """こんらんの「おもて」なら処理してねむりに置きかわり、「うら」なら自分に 20（自分の弱点が超なので 40。p.322）で効果なし（kyuura の
        CR-COLLAPSE-SPECIAL-CONDITIONS の当てはめ）。ねむり・マヒでは宣言できない。"""
        state = board(slowpoke(confusion=True), PONYTA)
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertTrue(new.players[0].active.conditions.asleep)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        expected = calculate_confusion_damage(load_card_pool().get(SABRINAS_SLOWPOKE), RULES_2000_02_14, 20).final
        self.assertEqual(expected, 40)
        self.assertEqual((new.players[0].active.conditions.confused, new.players[0].active.damage), (True, expected))
        for extra, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED")):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(board(slowpoke(**extra), PONYTA), UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(board({"card": SABRINAS_SLOWPOKE, "energy": [PSYCHIC]}, PONYTA), UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")


class NoDamageStopTest(unittest.TestCase):
    """Z23（docs/unresolved-research-v0.18b.md 3 章）: ダメージを与えなかった場合は、どの場合でも宣言の前に止まり、状態・乱数・ログが変わらない。"""

    def assert_stops(self, state, why):
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, NO_DAMAGE)
        self.assertIn(f"（{why}）", str(ctx.exception))
        self.assertIn(str(LAZY), str(ctx.exception))
        self.assertEqual(snapshot(state), before)

    def test_z23_b_resistance(self):
        """Z23-b: 抵抗力 超 −30 の相手で 30 − 30 = 0（たおれこむでは起こらない、ぐうたらこうげきの場合）。"""
        for target in PSYCHIC_RESISTANT:
            with self.subTest(target=target):
                self.assert_stops(board(slowpoke(), target), "最終ダメージが 0")

    def test_plus_power_against_resistance_is_not_stopped(self):
        """隣の止まらない場合: プラスパワーで 30 − 30 + 10 = 10（ダメージを与えた）。自分はねむりになる。"""
        state = board(slowpoke(trainers=[(PLUSPOWER, TURN)]), RATTATA)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual((events(new, len(state.log), "damage")[0]["amount"], new.players[0].active.conditions.asleep), (10, True))

    def test_z23_a_and_c(self):
        """Z23-a（かたまる）・Z23-c（化石の秘密のゴーストの「とうめい」。コインの結果によらない）。"""
        self.assert_stops(board(slowpoke(), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1}), "「ダメージを受けない」状態で無効")
        for side in (H, T):
            with self.subTest(coin=side):
                self.assert_stops(with_coin_results(board(slowpoke(), {"card": HAUNTER, "evolved_from": GASTLY}), side), "「とうめい」で受けなかった")

    def test_every_preflight_mode(self):
        """先読みの方法（derived・derived_full・比べる方法 legacy）によらず止まる。legacy も DamageAndSelfSleep（VERIFIED にない）はすべての結果を試す。"""
        for mode in PREFLIGHT_MODES:
            for target in (RATTATA, {"card": HAUNTER, "evolved_from": GASTLY}):
                with self.subTest(mode=mode, target=target):
                    state = board(slowpoke(), target)
                    before = snapshot(state)
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(state, UseAttack(0, 0), preflight=mode)
                    self.assertEqual(ctx.exception.code, NO_DAMAGE)
                    self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- 正式な開始（new_game）からの対戦

SLOWPOKE_DECK = expand_decklist({
    SABRINAS_SLOWPOKE: 4, GIOVANNIS_MEOWTH: 3, RATTATA: 3, DODUO: 3, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2, PSYCHIC: 35,
})
SEEDS = tuple(range(80))


def decks(seed):
    """seed を 4 で割った余りで相手（炎・いろいろなワザ・R団のカビゴン（抵抗力 超）・わるいカメール）、2 で割った余りで席を決める。"""
    opponent = (MOLTRES_DECK_A, MOLTRES_DECK_B, SNORLAX_DECK, WARTORTLE_DECK)[seed % 4]
    return (SLOWPOKE_DECK, opponent) if seed % 2 == 0 else (opponent, SLOWPOKE_DECK)


def no_damage_case(state, command):
    """Z23 で止まるのが正しいか（エンジンの関数を使わない。p.321 の計算を場から組み立てる）。ナツメのヤドンのぐうたらこうげき（超 30）・R団の
    カビゴンのたおれこむ（無 20）で、場合（docs/unresolved-research-v0.18b.md 3 章）を返す。止まらないはずなら None。"""
    me, target = state.players[command.player].active, state.players[1 - command.player].active
    kind = card_id(state, me)
    if kind not in (SABRINAS_SLOWPOKE, ROCKETS_SNORLAX):
        return None
    if any(isinstance(e, PreventDamage) and e.active_turn == state.turn_number for e in target.persistent_effects):
        return "Z23-a"
    attacker, defender = state.card_def(me.card), state.card_def(target.card)
    amount = attacker.attacks[0].damage
    if defender.weakness is attacker.pokemon_type:
        amount *= 2
    resisted = defender.resistance is attacker.pokemon_type
    if resisted:
        amount -= defender.resistance_value
    amount += 10 * sum(state.cards[t.card].card_id == PLUSPOWER for t in me.trainers)
    amount -= 20 * sum(state.cards[t.card].card_id == DEFENDER for t in target.trainers)
    if amount <= 0:
        return "Z23-b-resistance" if resisted else "Z23-b-defender"
    return "Z23-c" if evasion_working(state, target) else None


def count(state):
    counted = Counter()
    for e in state.log:
        if e["kind"] == "special_condition" and e.get("effect") == str(LAZY):
            counted["lazy_self_sleep"] += 1
        elif e["kind"] == "sleep_check":
            counted["sleep_check"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    return counted


def play(seed):
    """対戦を進め、Z23 で止まった場面を場合ごとに数える（``observed`` の ``z23_<場合>_<カード>``）。"""
    cases = Counter()

    def stop(state, command):
        case = no_damage_case(state, command)
        if case is not None:
            cases[f"z23_{case}_{card_id(state, state.players[command.player].active)}"] += 1
        return case is not None

    state, commands, observed = play_game(decks(seed), seed, cure=seed % 3 != 0, not_declarable=(ROCKETS_SNORLAX,), extra_stop={NO_DAMAGE: stop},
                                          double_ko_check=lambda s, t: counter_working(s, t) or restless_working(s, t))
    observed.update(cases)
    return state, commands, observed


class NaturalGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play(seed) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(observed)
            counted.update(count(state))
        return counted

    def test_counts(self):
        """自然な対戦の中で、ぐうたらこうげきで自分をねむりにし、Z23 で止まり（抵抗力の相手を含む）、ねむりのヤドンはワザを宣言できない
        （1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in (f"attack_{LAZY}", "lazy_self_sleep", f"stopped_attack_{NO_DAMAGE}", "rejected_attack_POKEMON_ASLEEP", "sleep_check"):
            self.assertGreater(counted[key], 0, (key, dict(counted)))
        self.assertEqual(counted["phase_game_over"] + counted["phase_halted"], len(SEEDS))

    def test_resistance_stop_happens_in_natural_games(self):
        """抵抗力 超 の相手（R団のカビゴン・コラッタ・サカキのニャース）に対して、ぐうたらこうげきが Z23-b で止まる場面が自然な対戦で起こる
        （たおれこむ（無色）では起こらない場合）。止まった場面は、どれも場から組み立てた場合のどれかに当たる。"""
        counted = self.total()
        self.assertGreater(counted[f"z23_Z23-b-resistance_{SABRINAS_SLOWPOKE}"], 0, dict(counted))
        self.assertEqual(counted[f"z23_Z23-b-resistance_{ROCKETS_SNORLAX}"], 0)
        self.assertEqual(sum(v for k, v in counted.items() if k.startswith("z23_")), counted[f"stopped_attack_{NO_DAMAGE}"])

    def test_invariants_logs_and_serialization(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay_and_save_restore(self):
        """同じ seed・同じ操作の列で同じ結果。ねむりのナツメのヤドンがいる状態で保存（pickle）して再開しても同じ。"""
        restored = 0
        for seed, (state, commands, _) in self.games.items():
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                if any(p.active is not None and card_id(replayed, p.active) == SABRINAS_SLOWPOKE and p.active.conditions.asleep
                       for p in replayed.players):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreater(restored, 0)


class GoldenGameTest(unittest.TestCase):
    """GOLDEN_SEED の対戦の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.18c）。手順・デッキ・乱数の使い方が変わると変わる。"""

    # ぐうたらこうげきで自分をねむりにし、抵抗力 超 の相手で Z23-b で止まった対戦（v0.18c）
    GOLDEN_SEED = 10
    GOLDEN = (123, 38, Phase.GAME_OVER, "7e42c23cce958450ab86ef0f59026ad00e33f1f722ed23715053bee7f50c84a4")

    def test_seed(self):
        state, commands, observed = play(self.GOLDEN_SEED)
        self.assertGreater(count(state)["lazy_self_sleep"], 0)
        self.assertGreater(observed[f"z23_Z23-b-resistance_{SABRINAS_SLOWPOKE}"], 0)
        data = full(state)
        # v0.69: 写しの元を上げた（7d3f4ca）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT_SINCE_V0_69)
        data = with_card_data_commit_before_v0_69(data)
        data.pop("effects")
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual((len(commands), state.turn_number, state.phase, digest), self.GOLDEN)


if __name__ == "__main__":
    unittest.main()
