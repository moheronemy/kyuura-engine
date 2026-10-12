"""特殊状態 4 種類の総合検証（v0.3d）: 8 つの状態の組み合わせ × 付与・上書き・解除・操作・ポケモンチェック。

どく（``SpecialConditions.poison``）はほかの特殊状態と重複し、ねむり・マヒ・こんらん（``exclusive``）はたがいに重複しない
（p.322「特殊状態の重複」）ので、バトル場のポケモンがとりうる特殊状態は次の 8 つ:

    なし・どく・ねむり・どく + ねむり・マヒ・どく + マヒ・こんらん・どく + こんらん

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・sleep・paralysis・
confusion_attack・confusion_retreat）:

- p.309 ワザを使う手順 1〜6（ねむり・マヒは宣言できない、こんらんは手順 5 のコイン）
- pp.310〜311 にげる（ねむり・マヒは宣言できない、こんらんは手順 3 のコイン、失敗したポケモンは同じ番にもう宣言できない、
  ベンチに戻ったら「どく」「ねむり」「マヒ」「こんらん」はすべて消える）
- p.322 特殊状態（2 ねむり・3 マヒ・4 こんらん・特殊状態の重複。特殊状態でもエネルギーカードをつけられる）
- p.323 15 ポケモンチェック（1 指示 → 2 どく → 3 ねむり → 4 マヒ。こんらんの手順はない）
- p.325 21 ポケモンの入れ替え（「にげる」がおこなえない状態のポケモンでも、入れ替えるよう指示されたら入れ替える）

それぞれの規定の分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/special-conditions-audit-v0.3d.md。
"""

import copy
import json
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayBasicToBench, PlayTrainer, ResolveDecision, Retreat, UnsupportedError,
    UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.conditions import confuse, paralyze, poison, put_to_sleep
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import ASLEEP, CONFUSED, NO_SPECIAL_CONDITIONS, Paralyzed, Poison, SpecialConditions

from tests.helpers import (
    BILL, FIRE, GROWLITHE, H, PONYTA, RATTATA, SWITCH, T, VULPIX, build_test_state, with_coin_results,
)

# 8 つの特殊状態（build_test_state のバトル場の指定）。マヒは前の番（2 番、相手の番）になったもの = 今の番（3 番）の
# 終わりのポケモンチェックで回復する（p.322・p.323）
STATES = {
    "none": {},
    "poison": {"poison": 10},
    "sleep": {"sleep": True},
    "poison+sleep": {"poison": 10, "sleep": True},
    "paralysis": {"paralysis": 2},
    "poison+paralysis": {"poison": 10, "paralysis": 2},
    "confusion": {"confusion": True},
    "poison+confusion": {"poison": 10, "confusion": True},
}
EXPECTED = {
    "none": NO_SPECIAL_CONDITIONS,
    "poison": SpecialConditions(poison=Poison(10)),
    "sleep": SpecialConditions(exclusive=ASLEEP),
    "poison+sleep": SpecialConditions(poison=Poison(10), exclusive=ASLEEP),
    "paralysis": SpecialConditions(exclusive=Paralyzed(2)),
    "poison+paralysis": SpecialConditions(poison=Poison(10), exclusive=Paralyzed(2)),
    "confusion": SpecialConditions(exclusive=CONFUSED),
    "poison+confusion": SpecialConditions(poison=Poison(10), exclusive=CONFUSED),
}
SERIALIZED = {
    "none": {},
    "poison": {"poison": {"damage": 10}},
    "sleep": {"sleep": {}},
    "poison+sleep": {"poison": {"damage": 10}, "sleep": {}},
    "paralysis": {"paralysis": {"turn": 2}},
    "poison+paralysis": {"poison": {"damage": 10}, "paralysis": {"turn": 2}},
    "confusion": {"confusion": {}},
    "poison+confusion": {"poison": {"damage": 10}, "confusion": {}},
}
CONFUSE_RAY = 0


def full(state):
    return state_to_dict(state, format_version=6)


def kinds(events):
    return [e["kind"] for e in events]


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def board(name, *sides, energy=(FIRE, FIRE, FIRE), hand_cards=(SWITCH, BILL, FIRE, RATTATA), opponent=None):
    """プレイヤー 0（3 番の番）のバトル場のロコン（炎・HP50・にげる 1）が ``STATES[name]``。控えはポニータ。
    プレイヤー 1 はガーディ（控えにコラッタ）。"""
    state = build_test_state([
        {"active": {"card": VULPIX, "energy": list(energy), **STATES[name]}, "bench": [PONYTA], "hand": list(hand_cards)},
        {"active": opponent or GROWLITHE, "bench": [RATTATA]},
    ])
    return with_coin_results(state, *sides) if sides else state


def run(state, command):
    start = len(state.log)
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[start:]]


def assert_rejected(test, state, command, code):
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(EngineError) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


def coin_sources(events):
    return [e["source"] for e in events if e["kind"] == "coin_flip"]


# ---------------------------------------------------------------- 15.1 状態そのもの


class EightStatesTest(unittest.TestCase):
    def test_every_combination_is_held_and_valid(self):
        """8 つの組み合わせをすべて持てて、不変条件を満たす。名前の順は p.322 の順（どく → ねむり・マヒ・こんらん）。"""
        for name, expected in EXPECTED.items():
            with self.subTest(state=name):
                state = board(name)
                conditions = state.players[0].active.conditions
                self.assertEqual(conditions, expected)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(conditions.names(), tuple(n for n in ("poison", "sleep", "paralysis", "confusion") if n in name))
                self.assertEqual((conditions.asleep, conditions.paralyzed, conditions.confused),
                                 ("sleep" in name, "paralysis" in name, "confusion" in name))

    def test_serialization_and_copies(self):
        """形式 5・6 で書き出せる。形式 1〜4 は特殊状態を表せないので ``ValueError``（なしの状態は書ける）。
        clone・deepcopy・pickle・JSON で同じ。"""
        for name in STATES:
            with self.subTest(state=name):
                state = board(name)
                for version in (5, 6):
                    data = state_to_dict(state, format_version=version)
                    self.assertEqual(data["players"][0]["active"]["special_conditions"], SERIALIZED[name])
                    json.dumps(data)
                for version in (1, 2, 3, 4):
                    if name == "none":
                        state_to_dict(state, format_version=version)
                    else:
                        with self.assertRaises(ValueError):
                            state_to_dict(state, format_version=version)
                for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                    self.assertEqual(full(copied), full(state))
                    self.assertEqual(copied.players[0].active.conditions, EXPECTED[name])

    def test_bench_pokemon_never_hold_them(self):
        """特殊状態になるのはバトル場のポケモンだけ（p.322）。ベンチにあれば不変条件の違反。"""
        for name, expected in EXPECTED.items():
            if name == "none":
                continue
            with self.subTest(state=name):
                state = board("none")
                state.players[0].bench[0].conditions = expected
                self.assertTrue(any("ベンチ" in problem for problem in check_invariants(state)))


# ---------------------------------------------------------------- 15.1 付与と上書き


APPLY = {"sleep": put_to_sleep, "paralysis": paralyze, "confusion": confuse, "poison": poison}
NEW_VALUE = {"sleep": ASLEEP, "paralysis": Paralyzed(3), "confusion": CONFUSED}


class OverwriteMatrixTest(unittest.TestCase):
    """ねむり・マヒ・こんらんの 3 × 3 の上書きと、どくのあり・なし（p.322）。マヒは、同じ番（3 番）にマヒ状態になったもの
    を前の状態にする（再付与で回復する番が変わらない場合。変わる場合は ``test_reparalysis_with_another_recovery_turn``）。"""

    def before(self, previous, poisoned):
        spec = {"sleep": {"sleep": True}, "paralysis": {"paralysis": 3}, "confusion": {"confusion": True}, None: {}}[previous]
        if poisoned:
            spec = {**spec, "poison": 10}
        return build_test_state([{"active": {"card": GROWLITHE, **spec}, "bench": [PONYTA]}, {"active": RATTATA}])

    def test_every_transition(self):
        for previous in (None, "sleep", "paralysis", "confusion"):
            for new in ("sleep", "paralysis", "confusion"):
                for poisoned in (False, True):
                    with self.subTest(previous=previous, new=new, poisoned=poisoned):
                        state = self.before(previous, poisoned)
                        target = state.players[0].active
                        old_exclusive = target.conditions.exclusive
                        start = len(state.log)
                        APPLY[new](state, 0, target, effect="test")
                        events = [dict(e) for e in state.log[start:]]
                        self.assertEqual(target.conditions.poison, Poison(10) if poisoned else None)  # どくは残る（C11）
                        applied = events[-1]
                        self.assertEqual((applied["kind"], applied["condition"]), ("special_condition", new))
                        if previous == new:
                            # 二重にならない（S9・P9・C4）。状態は変わらず、ログに already
                            self.assertEqual(target.conditions.exclusive, old_exclusive)
                            self.assertTrue(applied["already"])
                            self.assertEqual(kinds(events), ["special_condition"])
                        else:
                            self.assertEqual(target.conditions.exclusive, NEW_VALUE[new])
                            self.assertNotIn("already", applied)
                            if previous is None:
                                self.assertEqual(kinds(events), ["special_condition"])
                            else:
                                # 前の状態が先に消える（reason replaced）。O2・O3・C9・C10
                                self.assertEqual(kinds(events), ["special_conditions_removed", "special_condition"])
                                self.assertEqual((events[0]["conditions"], events[0]["reason"]), ((previous,), "replaced"))
                        self.assertEqual(check_invariants(state), [])

    def test_poison_joins_every_exclusive_state(self):
        """どくはほかの特殊状態と重複する（p.322）。ねむり・マヒ・こんらんは変わらない。"""
        for previous in (None, "sleep", "paralysis", "confusion"):
            for poisoned in (False, True):
                with self.subTest(previous=previous, poisoned=poisoned):
                    state = self.before(previous, poisoned)
                    target = state.players[0].active
                    exclusive = target.conditions.exclusive
                    poison(state, 0, target, effect="test")
                    self.assertEqual(target.conditions, SpecialConditions(poison=Poison(10), exclusive=exclusive))
                    self.assertEqual(state.log[-1].get("already", False), poisoned)

    def test_reparalysis_with_another_recovery_turn(self):
        """マヒの再付与で回復する番が変わる場合は原典で決められない（UNRESOLVED。P10）。状態を変えずに止める。"""
        for poisoned in (False, True):
            with self.subTest(poisoned=poisoned):
                state = build_test_state([
                    {"active": {"card": GROWLITHE, "paralysis": 2, **({"poison": 10} if poisoned else {})}, "bench": [PONYTA]},
                    {"active": RATTATA},
                ])
                before = full(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    paralyze(state, 0, state.players[0].active, effect="test")
                self.assertEqual(ctx.exception.code, "UNRESOLVED_REPARALYSIS_RECOVERY_TURN")
                self.assertEqual(full(state), before)


# ---------------------------------------------------------------- 15.2 操作 × 8 つの状態


class AttackMatrixTest(unittest.TestCase):
    """ワザ（ロコンの「あやしいひかり」）: なし・どくは使える。ねむり・マヒはコインの前に拒否（p.309）。こんらんは宣言のあと
    にこんらんのコイン（「おもて」ならワザ、「うら」なら自分に 20）。"""

    def test_attack_in_every_state(self):
        for name in STATES:
            for side in (H, T):
                with self.subTest(state=name, side=side):
                    state = board(name, side, side, side)
                    if "sleep" in name:
                        assert_rejected(self, state, UseAttack(0, CONFUSE_RAY), "POKEMON_ASLEEP")
                        continue
                    if "paralysis" in name:
                        assert_rejected(self, state, UseAttack(0, CONFUSE_RAY), "POKEMON_PARALYZED")
                        continue
                    vulpix = state.players[0].active
                    new, events = run(state, UseAttack(0, CONFUSE_RAY))
                    sources = coin_sources(events)
                    after = new.find_pokemon(vulpix.pokemon_id)[1]
                    poisoned = 10 if "poison" in name else 0  # 番の終わりのポケモンチェックのどく
                    if "confusion" in name and side is T:
                        self.assertEqual(sources, ["confusion"])  # ワザの説明のコインはない
                        self.assertNotIn("damage", kinds(events))
                        self.assertEqual(after.damage, 20 + poisoned)
                    else:
                        self.assertEqual(sources, (["confusion"] if "confusion" in name else []) + ["attack"])
                        self.assertEqual(new.players[1].active.damage, 10)
                        self.assertEqual(after.damage, poisoned)
                    self.assertEqual(after.conditions, EXPECTED[name])  # ワザを使っても自分の状態は変わらない
                    self.assertEqual((new.current_player, new.turn_number), (1, 4))  # ワザは使ったことになり番が終わる
                    self.assertEqual(check_invariants(new), [])


class RetreatMatrixTest(unittest.TestCase):
    """にげる: なし・どくはコインなしで入れ替え（どくは消える）。ねむり・マヒはエネルギーの前に拒否（p.311）。こんらんは
    エネルギーをトラッシュしてからコイン（「おもて」なら入れ替えてすべて消える、「うら」なら失敗し記録が付く）。"""

    def test_retreat_in_every_state(self):
        for name in STATES:
            for side in (H, T):
                with self.subTest(state=name, side=side):
                    state = board(name, side)
                    vulpix, ponyta = state.players[0].active, state.players[0].bench[0]
                    command = Retreat(0, (vulpix.energy[0],), ponyta.card)
                    if "sleep" in name:
                        assert_rejected(self, state, command, "POKEMON_ASLEEP")
                        continue
                    if "paralysis" in name:
                        assert_rejected(self, state, command, "POKEMON_PARALYZED")
                        continue
                    new, events = run(state, command)
                    after = new.find_pokemon(vulpix.pokemon_id)[1]  # 場のポケモンの番号は変わらない
                    self.assertEqual(coin_sources(events), ["confusion"] if "confusion" in name else [])
                    self.assertIn(vulpix.energy[0], new.players[0].discard)  # エネルギーはトラッシュ（失敗でも）
                    if "confusion" in name and side is T:
                        self.assertIs(new.players[0].active, after)
                        self.assertEqual((after.conditions, after.retreat_failed_turn), (EXPECTED[name], 3))
                        self.assertEqual(kinds(events)[-1], "retreat_failed")
                    else:
                        self.assertIs(new.players[0].bench[0], after)
                        self.assertEqual((after.conditions, after.retreat_failed_turn), (NO_SPECIAL_CONDITIONS, None))
                        self.assertEqual(new.players[0].active.pokemon_id, ponyta.pokemon_id)
                    self.assertEqual((new.phase, new.current_player), (Phase.MAIN, 0))  # 番は続く
                    self.assertEqual(check_invariants(new), [])


class OtherActionsMatrixTest(unittest.TestCase):
    """ポケモンいれかえ（p.325）はどの状態でもコインなしで入れ替え、ベンチに戻ったポケモンの特殊状態はすべて消える。
    トレーナー（マサキ）・エネルギー・ベンチに出す・番を終えるは、どの状態でもできる（p.322）。"""

    def test_switch_in_every_state(self):
        for name in STATES:
            with self.subTest(state=name):
                state = board(name)
                vulpix, ponyta = state.players[0].active, state.players[0].bench[0]
                fingerprint = rng_fingerprint(state.rng)
                new, _ = run(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
                new, events = run(new, ResolveDecision(0, new.decision.id, (ponyta.pokemon_id,)))
                self.assertEqual(rng_fingerprint(new.rng), fingerprint)
                back = new.find_pokemon(vulpix.pokemon_id)[1]
                self.assertIs(new.players[0].bench[0], back)
                self.assertEqual(back.conditions, NO_SPECIAL_CONDITIONS)
                removed = [e for e in events if e["kind"] == "special_conditions_removed"]
                self.assertEqual([(e["conditions"], e["reason"]) for e in removed],
                                 [] if name == "none" else [(EXPECTED[name].names(), "switch")])
                self.assertEqual(check_invariants(new), [])

    def test_other_actions_in_every_state(self):
        for name in STATES:
            with self.subTest(state=name):
                state = board(name)
                fingerprint = rng_fingerprint(state.rng)
                state, _ = run(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
                state, _ = run(state, AttachEnergy(0, hand(state, 0, FIRE)[0], state.players[0].active.card))
                state, _ = run(state, PlayBasicToBench(0, hand(state, 0, RATTATA)[0]))
                self.assertEqual(rng_fingerprint(state.rng), fingerprint)  # どれも乱数を使わない
                self.assertEqual(state.players[0].active.conditions, EXPECTED[name])
                self.assertEqual(check_invariants(state), [])


class PendingDecisionMatrixTest(unittest.TestCase):
    """決定を待つ間（ポケモンチェックのどくで相手のポケモンがきぜつし、サイドを取る決定）は、どの状態でも番のプレイヤーの
    操作を受け付けない。拒否は状態も乱数も変えない（ねむりのコイン・こんらんのコインを先に投げない）。"""

    def test_actions_are_rejected_while_a_decision_is_pending(self):
        for name in STATES:
            with self.subTest(state=name):
                state = board(name, opponent={"card": GROWLITHE, "poison": 10, "damage": 50})
                state = apply_command(state, EndTurn(0))
                self.assertEqual((state.phase, state.decision.player, state.decision.kind), (Phase.TAKE_PRIZE, 0, "take_prize"))
                vulpix = state.players[0].active
                self.assertEqual(vulpix.conditions.exclusive, EXPECTED[name].exclusive)  # 3・4 はまだ
                for command in (UseAttack(0, CONFUSE_RAY), Retreat(0, (vulpix.energy[0],), state.players[0].bench[0].card),
                                PlayTrainer(0, hand(state, 0, BILL)[0]), AttachEnergy(0, hand(state, 0, FIRE)[0], vulpix.card),
                                EndTurn(0), EndTurn(1)):
                    with self.assertRaises(EngineError):
                        before, fingerprint = full(state), rng_fingerprint(state.rng)
                        try:
                            apply_command(state, command)
                        finally:
                            self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


# ---------------------------------------------------------------- 15.4 ポケモンチェック × 8 つの状態


class PokemonCheckMatrixTest(unittest.TestCase):
    """番を終えたあとのポケモンチェック（p.323）: 2 どく 10 → 3 ねむりのコイン（持ち主）→ 4 マヒの回復（マヒ状態になった番
    の次の持ち主の番の終わり）。こんらんは何もしない（自然に回復しない。p.322）。番と番のあいだに 1 回だけ。"""

    def test_check_in_every_state(self):
        for name in STATES:
            for side in (H, T):
                with self.subTest(state=name, side=side):
                    state = board(name, side)
                    vulpix = state.players[0].active
                    new, events = run(state, EndTurn(0))
                    after = new.players[0].active
                    self.assertIs(after, new.find_pokemon(vulpix.pokemon_id)[1])
                    self.assertEqual((kinds(events).count("turn_end"), kinds(events).count("pokemon_check")), (1, 1))
                    check = kinds(events).index("pokemon_check")
                    self.assertEqual(after.damage, 10 if "poison" in name else 0)
                    flips = [e for e in events if e["kind"] == "coin_flip"]
                    if "sleep" in name:
                        self.assertEqual([(e["player"], e["source"], e["effect"]) for e in flips], [(0, "pokemon_check", "sleep")])
                        self.assertGreater(kinds(events).index("coin_flip"), check)
                        self.assertEqual(after.conditions.asleep, side is T)
                    else:
                        self.assertEqual(flips, [])  # ねむりがなければ乱数を使わない
                    if "paralysis" in name:
                        self.assertFalse(after.conditions.paralyzed)  # 2 番（相手の番）にマヒ → 3 番の終わりに回復
                        removed = [e for e in events if e["kind"] == "special_conditions_removed"]
                        self.assertEqual(removed[-1]["reason"], "paralysis_end")
                    if "confusion" in name:
                        self.assertTrue(after.conditions.confused)
                    self.assertEqual(after.conditions.poison, Poison(10) if "poison" in name else None)
                    self.assertEqual((new.current_player, new.turn_number, new.phase), (1, 4, Phase.MAIN))
                    self.assertEqual(check_invariants(new), [])

    def test_opponent_paralysis_received_this_turn_does_not_recover_yet(self):
        """相手の番（3 番。プレイヤー 0 の番）にマヒ状態になったプレイヤー 1 のポケモンは、3 番の終わりには回復せず、
        持ち主の次の番（4 番）の終わりに回復する（p.322「次の自分（そのポケモンの持ち主）の番」）。"""
        state = board("none", opponent={"card": GROWLITHE, "paralysis": 3})
        state = apply_command(state, EndTurn(0))
        self.assertTrue(state.players[1].active.conditions.paralyzed)
        state = apply_command(state, EndTurn(1))
        self.assertFalse(state.players[1].active.conditions.paralyzed)

    def test_poison_knock_out_in_every_exclusive_state(self):
        """どくできぜつしたポケモンの特殊状態はいっしょになくなり、ねむりのコインは投げない（p.323。v0.3b）。"""
        for name in ("poison", "poison+sleep", "poison+paralysis", "poison+confusion"):
            with self.subTest(state=name):
                state = build_test_state([
                    {"active": {"card": VULPIX, "damage": 40, **STATES[name]}, "bench": [PONYTA]},
                    {"active": GROWLITHE, "bench": [RATTATA]},
                ])
                new, events = run(state, EndTurn(0))
                self.assertIn("knock_out", kinds(events))
                self.assertNotIn("coin_flip", kinds(events))
                self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 1))
                new = apply_command(new, ResolveDecision(1, new.decision.id, (0,)))
                new = apply_command(new, ResolveDecision(0, new.decision.id, (new.decision.options[0],)))
                self.assertEqual(new.players[0].active.conditions, NO_SPECIAL_CONDITIONS)  # ベンチから出たポケモン
                self.assertEqual((new.current_player, new.turn_number), (1, 4))
                self.assertEqual(check_invariants(new), [])


if __name__ == "__main__":
    unittest.main()
