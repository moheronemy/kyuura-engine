"""こんらん（v0.3c）: 状態の付与・重複と上書き・続くこと・ポケモンチェック・ポケモンいれかえ・状態の保存・不変条件。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES、rule_differences.json の
confusion_attack・confusion_retreat の「2000年2月」の行）:

- p.322「4. こんらん状態」: 「ポケモンがこんらん状態になったら、そのポケモンのカードを上下逆さまにします」「ポケモンの
  こんらん状態が自然に回復することは、ありません」「こんらん状態のポケモンが再びこんらん状態になる効果を受けても、二重の
  こんらん状態になるわけではありません。こんらん状態が積み重なることはありません」
- p.322「特殊状態の重複」: 「「ねむり」「マヒ」「こんらん」状態が重複することはありません」（マヒ状態のポケモンがねむり状態に
  なったら、マヒから自動的に回復してねむり状態になる例）。「どく状態は、他の特殊状態と重複します。こんらん状態のポケモンが
  どく状態になったら、そのポケモンは「どく」と「こんらん」の両方の状態になります」
- p.311: 「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態や、「持続する効果」は、すべて消えて
  なくなります」
- p.323「ポケモンチェックでおこなうことの順番」: 1〜4（「どく」「ねむり」「マヒ」）にこんらんはない
- p.325「21 ポケモンの入れ替え」: 「にげる」がおこなえない状態のポケモンでも、「そのポケモンを入れ替える」と指示された
  ときは、入れ替えをおこなう

ワザのこんらんは test_confusion_attacks.py、にげるのこんらんは test_confusion_retreat.py、正式な対戦開始からは
test_confusion_games.py。分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/confusion-v0.3c.md。
"""

import copy
import dataclasses
import json
import pickle
import unittest

from kyuura_engine import (
    EndTurn, Phase, PlayTrainer, ResolveDecision, Retreat, UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.conditions import confuse, paralyze, poison, put_to_sleep
from kyuura_engine.rng import rng_fingerprint, rng_from_json, rng_state_to_json
from kyuura_engine.state import (
    ASLEEP, CONFUSED, NO_SPECIAL_CONDITIONS, Asleep, Confused, Paralyzed, Poison, SpecialConditions,
)

from tests.helpers import (
    CATERPIE, FIRE, GRASS, GROWLITHE, H, PARAS, PONYTA, RATTATA, SWITCH, T, VULPIX, WEEDLE, build_test_state,
    with_coin_results,
)

CONFUSE_RAY = 0  # ロコンの「あやしいひかり」
STRING_SHOT = 0  # キャタピーの「いとをはく」
SPORE = 1  # パラスの「キノコのほうし」
POISON_STING = 0  # ビードルの「どくばり」


def full(state):
    return state_to_dict(state, format_version=6)


def kinds(events):
    return [e["kind"] for e in events]


def use(state, player, index):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, index))
    return new, [dict(e) for e in new.log[start:]]


def board(attacker, defender_spec, *sides, energy=(FIRE, FIRE)):
    """プレイヤー 0（3 番）の ``attacker`` が、プレイヤー 1 の対戦ポケモン（``defender_spec``）にワザを使う盤面。"""
    spec = {"card": GROWLITHE} | dict(defender_spec)
    state = build_test_state([
        {"active": {"card": attacker, "energy": list(energy)}, "bench": [PONYTA]},
        {"active": spec, "bench": [RATTATA]},
    ])
    return with_coin_results(state, *sides) if sides else state


def record_failure(state, pokemon, player=0):
    """テスト用: ``pokemon`` がこの番に「にげる」に失敗した記録と、それに対応するログ（v0.3d の不変条件）を置く。"""
    pokemon.retreat_failed_turn = state.turn_number
    state.add_event("retreat_failed", player=player, pokemon=pokemon.card, pokemon_id=pokemon.pokemon_id, discarded=())


def confused_board(*, bench=(PONYTA,), hand_cards=(), poisoned=False, energy=(FIRE,)):
    """プレイヤー 0（3 番の番）の対戦ポケモンのロコンがこんらん状態。"""
    spec = {"card": VULPIX, "energy": list(energy), "confusion": True}
    if poisoned:
        spec["poison"] = 10
    return build_test_state([
        {"active": spec, "bench": list(bench), "hand": list(hand_cards)},
        {"active": GROWLITHE, "bench": [RATTATA]},
    ])


# ---------------------------------------------------------------- 付与（14.1）


class ConfuseTest(unittest.TestCase):
    def test_confuse_ray_heads_confuses_the_defending_pokemon(self):
        """ロコンの「あやしいひかり」（p.67）: 相手に 10、コインが「おもて」なら相手をこんらん状態にする（p.322）。"""
        state = board(VULPIX, {}, H)
        target = state.players[1].active
        new, events = use(state, 0, CONFUSE_RAY)
        self.assertEqual(kinds(events)[:4], ["attack", "damage", "coin_flip", "special_condition"])
        applied = events[3]
        self.assertEqual({k: applied[k] for k in ("player", "pokemon", "pokemon_id", "condition", "effect")},
                         {"player": 1, "pokemon": target.card, "pokemon_id": target.pokemon_id, "condition": "confusion",
                          "effect": "PMCG1-015#0"})
        self.assertNotIn("already", applied)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=CONFUSED))
        self.assertTrue(new.players[1].active.conditions.confused)
        self.assertEqual(new.players[1].active.conditions.names(), ("confusion",))
        self.assertEqual(check_invariants(new), [])

    def test_confused_is_a_shared_value_without_data(self):
        """こんらん状態は持つ情報がない（カードを上下逆さまにするだけ。p.322）。同じ値どうしは等しい。"""
        self.assertEqual(Confused(), CONFUSED)
        self.assertEqual(Confused.name, "confusion")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            CONFUSED.name = "x"

    def test_only_the_active_pokemon_can_be_confused(self):
        """特殊状態になるのはバトル場のポケモンだけ（p.322）。ベンチのポケモンをこんらん状態にするのはエンジンの不具合。"""
        state = confused_board()
        with self.assertRaises(RuntimeError):
            confuse(state, 0, state.players[0].bench[0], effect="test")


# ---------------------------------------------------------------- 重複と上書き（14.1）


class OverlapTest(unittest.TestCase):
    """p.322「特殊状態の重複」。ねむり・マヒ・こんらんは 1 つだけ（``SpecialConditions.exclusive``）。どくは別に持つ。"""

    def apply(self, spec, how):
        state = build_test_state([{"active": {"card": GROWLITHE} | spec, "bench": [PONYTA]}, {"active": RATTATA}])
        target = state.players[0].active
        start = len(state.log)
        if how == "confuse":
            confuse(state, 0, target, effect="test")
        elif how == "sleep":
            put_to_sleep(state, 0, target, effect="test")
        elif how == "paralyze":
            paralyze(state, 0, target, effect="test")
        else:
            poison(state, 0, target, effect="test")
        self.assertEqual(check_invariants(state), [])
        return target.conditions, [dict(e) for e in state.log[start:]]

    def test_sleep_and_paralysis_are_replaced_by_confusion(self):
        """ねむり・マヒ状態のポケモンがこんらん状態になったら、ねむり・マヒは消えてこんらん状態になる（p.322 の重複しない
        規定と、マヒ → ねむりの例を当てはめた。SUPPORTED）。どく状態はそのまま。"""
        for spec, removed in (({"sleep": True}, "sleep"), ({"paralysis": 2}, "paralysis"),
                              ({"sleep": True, "poison": 10}, "sleep"), ({"paralysis": 2, "poison": 10}, "paralysis")):
            with self.subTest(spec=spec):
                conditions, events = self.apply(spec, "confuse")
                self.assertEqual(conditions.exclusive, CONFUSED)
                self.assertEqual(conditions.poison, Poison(10) if "poison" in spec else None)
                self.assertEqual(kinds(events), ["special_conditions_removed", "special_condition"])
                self.assertEqual((events[0]["conditions"], events[0]["reason"]), ((removed,), "replaced"))

    def test_confusion_is_replaced_by_sleep_and_paralysis(self):
        """こんらん状態のポケモンがねむり・マヒ状態になったら、こんらんは消える（SUPPORTED）。どく状態はそのまま。"""
        for how, expected in (("sleep", ASLEEP), ("paralyze", Paralyzed(3))):
            for poisoned in (False, True):
                with self.subTest(how=how, poisoned=poisoned):
                    spec = {"confusion": True} | ({"poison": 10} if poisoned else {})
                    conditions, events = self.apply(spec, how)
                    self.assertEqual(conditions.exclusive, expected)
                    self.assertEqual(conditions.poison, Poison(10) if poisoned else None)
                    self.assertEqual((events[0]["conditions"], events[0]["reason"]), (("confusion",), "replaced"))

    def test_confusion_does_not_stack(self):
        """こんらん状態のポケモンが再びこんらん状態になっても二重にならない（p.322。CONFIRMED）。状態は変わらず、ログに already。"""
        conditions, events = self.apply({"confusion": True}, "confuse")
        self.assertEqual(conditions, SpecialConditions(exclusive=CONFUSED))
        self.assertEqual(kinds(events), ["special_condition"])
        self.assertTrue(events[0]["already"])

    def test_poison_and_confusion_overlap(self):
        """こんらん状態のポケモンがどく状態になったら「どく」と「こんらん」の両方の状態になる（p.322。CONFIRMED）。逆も同じ。"""
        conditions, _ = self.apply({"confusion": True}, "poison")
        self.assertEqual(conditions, SpecialConditions(poison=Poison(10), exclusive=CONFUSED))
        self.assertEqual(conditions.names(), ("poison", "confusion"))
        conditions, events = self.apply({"poison": 10}, "confuse")
        self.assertEqual(conditions, SpecialConditions(poison=Poison(10), exclusive=CONFUSED))
        self.assertEqual(kinds(events), ["special_condition"])  # どくは消さない

    def test_attacks_overwrite_in_play(self):
        """カードのワザで上書きする: あやしいひかり（「おもて」）でねむり → こんらん、キノコのほうしでこんらん → ねむり、
        いとをはく（「おもて」）でこんらん → マヒ、どくばり（「おもて」）でこんらん + どく。"""
        cases = (
            (VULPIX, CONFUSE_RAY, (FIRE, FIRE), {"sleep": True}, (H,), SpecialConditions(exclusive=CONFUSED)),
            (VULPIX, CONFUSE_RAY, (FIRE, FIRE), {"paralysis": 2}, (H,), SpecialConditions(exclusive=CONFUSED)),
            (VULPIX, CONFUSE_RAY, (FIRE, FIRE), {"poison": 10}, (H,), SpecialConditions(poison=Poison(10), exclusive=CONFUSED)),
            (VULPIX, CONFUSE_RAY, (FIRE, FIRE), {"confusion": True}, (H,), SpecialConditions(exclusive=CONFUSED)),
            # 2 枚目は番の終わりのポケモンチェックのねむりのコイン（「うら」なら続く）
            (VULPIX, CONFUSE_RAY, (FIRE, FIRE), {"sleep": True}, (T, T), SpecialConditions(exclusive=ASLEEP)),
            (PARAS, SPORE, (GRASS, GRASS), {"confusion": True}, (T,), SpecialConditions(exclusive=ASLEEP)),
            (CATERPIE, STRING_SHOT, (GRASS,), {"confusion": True}, (H,), SpecialConditions(exclusive=Paralyzed(3))),
            (WEEDLE, POISON_STING, (GRASS,), {"confusion": True}, (H,), SpecialConditions(poison=Poison(10), exclusive=CONFUSED)),
        )
        for attacker, index, energy, spec, sides, expected in cases:
            with self.subTest(attacker=attacker, spec=spec, sides=sides):
                new, _ = use(board(attacker, spec, *sides, energy=energy), 0, index)
                self.assertEqual(new.players[1].active.conditions, expected)
                self.assertEqual(check_invariants(new), [])


# ---------------------------------------------------------------- 続くこと・ポケモンチェック（14.1・9 章）


class PersistenceTest(unittest.TestCase):
    def test_confusion_does_not_recover_naturally(self):
        """こんらん状態は自然に回復しない（p.322）。ポケモンチェック（p.323 の 1〜4）にこんらんの手順はない。何番たっても続く。"""
        state = confused_board()
        pokemon_id = state.players[0].active.pokemon_id
        for _ in range(6):
            player = state.current_player
            start = len(state.log)
            fingerprint_before = rng_fingerprint(state.rng)
            state = apply_command(state, EndTurn(player))
            events = [dict(e) for e in state.log[start:]]
            self.assertEqual(kinds(events)[:4], ["end_turn_without_attack", "turn_end", "pokemon_check", "turn_start"])
            self.assertNotIn("coin_flip", kinds(events))  # こんらんのためのコインはない
            self.assertNotIn("special_conditions_removed", kinds(events))
            self.assertEqual(rng_fingerprint(state.rng), fingerprint_before)
            self.assertEqual(state.find_pokemon(pokemon_id)[1].conditions, SpecialConditions(exclusive=CONFUSED))
            self.assertEqual(check_invariants(state), [])
        self.assertEqual(state.turn_number, 9)

    def test_poison_damage_with_confusion(self):
        """どく + こんらん: ポケモンチェックの 2 でどくのダメージ（10）を受け、こんらんは残る（p.322・p.323）。"""
        state = confused_board(poisoned=True)
        start = len(state.log)
        new = apply_command(state, EndTurn(0))
        events = [dict(e) for e in new.log[start:]]
        self.assertEqual(kinds(events)[:5], ["end_turn_without_attack", "turn_end", "pokemon_check", "poison_damage", "turn_start"])
        vulpix = new.players[0].active
        self.assertEqual((vulpix.damage, vulpix.conditions), (10, SpecialConditions(poison=Poison(10), exclusive=CONFUSED)))

    def test_confused_pokemon_knocked_out_by_poison(self):
        """どくでこんらん状態のポケモンがきぜつしても、こんらんには関係しない（場をはなれ、特殊状態は残らない。p.322）。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE], "confusion": True, "poison": 10, "damage": 40}, "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ])
        new = apply_command(state, EndTurn(0))
        self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 1))
        self.assertEqual(check_invariants(new), [])

    def test_double_knockout_stop_is_unchanged(self):
        """両方の対戦ポケモンがポケモンチェックのどくできぜつする場合は、こんらんがあっても v0.3a と同じく止める
        （``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT``。この停止の条件は変えていない）。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE], "confusion": True, "poison": 10, "damage": 40}, "bench": [PONYTA]},
            {"active": {"card": RATTATA, "poison": 10, "damage": 20}, "bench": [GROWLITHE]},
        ])
        new = apply_command(state, EndTurn(0))
        self.assertEqual((new.phase, new.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"))

    def test_sleep_coin_order_stop_is_unchanged(self):
        """ねむりのコインの順番の停止（``UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER``）は、両方がねむりのときだけ。
        片方がこんらんなら、ねむりのポケモンの持ち主だけがコインを投げる。"""
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE], "confusion": True}, "bench": [PONYTA]},
            {"active": {"card": RATTATA, "sleep": True}, "bench": [GROWLITHE]},
        ])
        state = with_coin_results(state, T)
        start = len(state.log)
        new = apply_command(state, EndTurn(0))
        events = [dict(e) for e in new.log[start:]]
        flips = [e for e in events if e["kind"] == "coin_flip"]
        self.assertEqual([(e["player"], e["source"], e["effect"]) for e in flips], [(1, "pokemon_check", "sleep")])
        self.assertTrue(new.players[0].active.conditions.confused)
        both_asleep = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE], "sleep": True}, "bench": [PONYTA]},
            {"active": {"card": RATTATA, "sleep": True}, "bench": [GROWLITHE]},
        ])
        halted = apply_command(both_asleep, EndTurn(0))
        self.assertEqual(halted.halt.code, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER")

    def test_energy_and_trainers_can_be_played_while_confused(self):
        """こんらん状態でもエネルギーをつけられる・トレーナーを使える（p.322 の特殊状態の一般の規定。制限はワザとにげるだけ）。"""
        from kyuura_engine import AttachEnergy

        state = confused_board(hand_cards=[FIRE])
        energy = state.players[0].hand[0]
        new = apply_command(state, AttachEnergy(0, energy, state.players[0].active.card))
        self.assertIn(energy, new.players[0].active.energy)
        self.assertTrue(new.players[0].active.conditions.confused)


# ---------------------------------------------------------------- ポケモンいれかえ・にげるで消える（8 章）


class LeavingTheBattleFieldTest(unittest.TestCase):
    def test_switch_clears_confusion_without_a_coin(self):
        """ポケモンいれかえ（p.254）は「にげる」ではない（p.325）。こんらん状態でもコインを投げずに入れ替え、ベンチに戻った
        ポケモンのこんらん（とどく）は消える（p.311）。"""
        for poisoned in (False, True):
            with self.subTest(poisoned=poisoned):
                state = confused_board(hand_cards=[SWITCH], poisoned=poisoned)
                vulpix = state.players[0].active
                fingerprint = rng_fingerprint(state.rng)
                state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
                state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
                self.assertEqual(rng_fingerprint(state.rng), fingerprint)
                self.assertNotIn("confusion_check", kinds(state.log))
                back = state.find_pokemon(vulpix.pokemon_id)[1]
                self.assertIs(back, state.players[0].bench[0])
                self.assertEqual(back.conditions, NO_SPECIAL_CONDITIONS)
                removed = [e for e in state.log if e["kind"] == "special_conditions_removed"][-1]
                self.assertEqual((removed["conditions"], removed["reason"]),
                                 ((("poison", "confusion") if poisoned else ("confusion",)), "switch"))
                self.assertEqual(check_invariants(state), [])

    def test_confusion_does_not_come_back(self):
        """一度ベンチに戻って消えたこんらんは、バトル場に戻っても復活しない（p.322）。"""
        state = confused_board(hand_cards=[SWITCH, SWITCH])
        vulpix = state.players[0].active
        for _ in range(2):
            state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
            state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertIs(state.players[0].active, state.find_pokemon(vulpix.pokemon_id)[1])
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_retreat_success_clears_confusion(self):
        """こんらん状態で「にげる」に成功したら、ベンチに戻ったポケモンのこんらんは消える（p.311）。"""
        state = with_coin_results(confused_board(), H)
        vulpix = state.players[0].active
        new = apply_command(state, Retreat(0, (vulpix.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(new.find_pokemon(vulpix.pokemon_id)[1].conditions, NO_SPECIAL_CONDITIONS)
        removed = [e for e in new.log if e["kind"] == "special_conditions_removed"][-1]
        self.assertEqual((removed["conditions"], removed["reason"]), (("confusion",), "retreat"))


# ---------------------------------------------------------------- 状態の保存（12 章）


class SerializationTest(unittest.TestCase):
    def test_format_5_and_6_write_confusion(self):
        state = confused_board(poisoned=True)
        for version in (5, 6):
            with self.subTest(version=version):
                data = state_to_dict(state, format_version=version)
                self.assertEqual(data["players"][0]["active"]["special_conditions"], {"poison": {"damage": 10}, "confusion": {}})
                self.assertEqual(data["players"][1]["active"]["special_conditions"], {})
                json.dumps(data)
        self.assertNotIn("retreat_failed_turn", state_to_dict(state, format_version=5)["players"][0]["active"])
        six = state_to_dict(state, format_version=6)
        for p in six["players"]:
            for pokemon in [p["active"], *p["bench"]]:
                self.assertIsNone(pokemon["retreat_failed_turn"])

    def test_older_formats_refuse_confusion(self):
        """形式 1〜4 は特殊状態を表せないので、こんらん状態を黙って落とさず ``ValueError`` にする。"""
        state = confused_board()
        for version in (1, 2, 3, 4):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)

    def test_format_6_without_v0_3c_items_is_format_5_plus_none(self):
        """こんらん・にげるの失敗の記録のない状態では、形式 6 は形式 5 に ``retreat_failed_turn: None`` を加えただけ。"""
        state = build_test_state([{"active": {"card": GROWLITHE, "poison": 10}, "bench": [PONYTA]}, {"active": RATTATA}])
        five, six = state_to_dict(state, format_version=5), state_to_dict(state, format_version=6)
        self.assertEqual(six.pop("format_version"), 6)
        self.assertEqual(five.pop("format_version"), 5)
        for p in six["players"]:
            for pokemon in [p["active"], *p["bench"]]:
                self.assertIsNone(pokemon.pop("retreat_failed_turn"))
        self.assertEqual(five, six)

    def test_unknown_exclusive_condition_is_not_dropped(self):
        """書き出せない特殊状態は黙って落とさない（エンジンの不具合や、知らない状態を作った場合）。"""

        @dataclasses.dataclass(frozen=True)
        class Unknown:
            name = "unknown"

        state = confused_board()
        state.players[0].active.conditions = SpecialConditions(exclusive=Unknown())
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=6)

    def test_clone_deepcopy_pickle_keep_confusion_and_retreat_record(self):
        state = confused_board()
        record_failure(state, state.players[0].active)
        self.assertEqual(check_invariants(state), [])
        for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            with self.subTest(copied=type(copied)):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(copied.players[0].active.conditions, SpecialConditions(exclusive=CONFUSED))
                self.assertEqual(copied.players[0].active.retreat_failed_turn, 3)
        clone = state.clone()
        clone.players[0].active.retreat_failed_turn = None
        clone.players[0].active.conditions = NO_SPECIAL_CONDITIONS
        self.assertEqual(state.players[0].active.retreat_failed_turn, 3)
        self.assertTrue(state.players[0].active.conditions.confused)

    def test_rng_json_continues_the_same_confusion_coins(self):
        """乱数の状態を JSON で保存して戻すと、こんらんのコインも同じ結果になる（rng_state_to_json・rng_from_json）。"""
        state = confused_board(energy=(FIRE, FIRE))
        restored = state.clone()
        restored.rng = rng_from_json(json.loads(json.dumps(rng_state_to_json(state.rng))))
        a = apply_command(state, UseAttack(0, CONFUSE_RAY))
        b = apply_command(restored, UseAttack(0, CONFUSE_RAY))
        self.assertEqual(full(a), full(b))
        self.assertIn("confusion_check", kinds(a.log))


# ---------------------------------------------------------------- 不変条件（13 章）


class InvariantTest(unittest.TestCase):
    def test_confused_bench_pokemon_is_a_violation(self):
        state = confused_board()
        state.players[0].bench[0].conditions = SpecialConditions(exclusive=CONFUSED)
        self.assertTrue(any("ベンチ" in problem for problem in check_invariants(state)))

    def test_exclusive_slot_holds_one_known_condition(self):
        """ねむり・マヒ・こんらんは 1 つの項目にしか持てない（重複しない形）。知らない値なら違反。"""
        state = confused_board()
        state.players[0].active.conditions = SpecialConditions(exclusive="confusion")
        self.assertTrue(any("Confused" in problem for problem in check_invariants(state)))
        for value in (ASLEEP, Paralyzed(2), CONFUSED):
            state.players[0].active.conditions = SpecialConditions(exclusive=value)
            self.assertEqual(check_invariants(state), [], value)
        self.assertNotIsInstance(CONFUSED, (Asleep, Paralyzed))

    def test_retreat_failure_record(self):
        """「にげる」に失敗した記録は、今の番の、番のプレイヤーのポケモンにだけある（p.311「今の自分の番では」）。"""
        ok = confused_board()
        record_failure(ok, ok.players[0].active)
        self.assertEqual(check_invariants(ok), [])
        bench = confused_board()
        record_failure(bench, bench.players[0].bench[0])  # ベンチに戻ったあと（ポケモンいれかえ）も、その番の間は残る
        self.assertEqual(check_invariants(bench), [])
        for player, where, value in ((0, "active", 2), (0, "active", 4), (1, "active", 3), (0, "active", "3"), (0, "active", True)):
            with self.subTest(player=player, value=value):
                state = confused_board()
                getattr(state.players[player], where).retreat_failed_turn = value
                self.assertTrue(any("「にげる」に失敗した番" in problem for problem in check_invariants(state)))

    def test_retreat_failure_record_needs_the_failure_in_the_log(self):
        """v0.3d: 記録は、今の番のログの ``retreat_failed``（同じ場のポケモン）と対応する。失敗していないポケモンに記録が
        付いていたら違反（記録を書きかえる・付け間違える不具合を見つける）。"""
        state = confused_board()
        state.players[0].active.retreat_failed_turn = 3
        self.assertTrue(any("retreat_failed" in problem for problem in check_invariants(state)))
        other = confused_board()
        record_failure(other, other.players[0].bench[0])
        other.players[0].active.retreat_failed_turn = 3  # 失敗したのはベンチのポニータで、バトル場のロコンではない
        self.assertTrue(any("retreat_failed" in problem for problem in check_invariants(other)))

    def test_retreat_failure_record_does_not_survive_the_end_of_turn(self):
        state = confused_board()
        state.players[0].active.retreat_failed_turn = 3
        state.add_event("turn_end", player=0)  # 番の終わりのあと（ポケモンチェックの途中）に残っていたら違反
        self.assertTrue(any("番の終わりのあと" in problem for problem in check_invariants(state)))

    def test_retreat_failure_record_in_setup_is_a_violation(self):
        state = confused_board()
        state.players[0].active.retreat_failed_turn = 3
        state.phase = Phase.SETUP_FIRST_PLAYER
        self.assertTrue(any("「にげる」に失敗した番" in problem for problem in check_invariants(state)))


if __name__ == "__main__":
    unittest.main()
