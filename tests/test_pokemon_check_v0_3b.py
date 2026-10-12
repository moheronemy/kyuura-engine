"""ポケモンチェックの 3（ねむり）・4（マヒ）（v0.3b）と、2（どく）のきぜつとの順番。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・knockout_timing）:

- p.323「15 ポケモンチェック」: どちらのプレイヤーの番でもない。順番は 1 指示されたこと → 2「どく」のダメージ →
  3「「ねむり」からさめるかどうかをチェックする」（「ねむり状態になっているポケモンの側のプレイヤーは、コインを投げます。
  「おもて」が出たら、そのプレイヤーのポケモンは、ねむり状態から回復します」）→ 4「「マヒ」がなおるかどうかをチェックする」
  （「マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで自動的に回復します」）。
  1 の「ここでおこなうことが複数あった場合には、このポケモンチェックの前に番をおこなったプレイヤーが、その順番を決めます」
  は 1 についての記述で、3 のコインの順番は書かれていない
- p.322: ねむり状態のポケモンの側のプレイヤーは「ポケモンチェックのたびに」コインを投げる。「うら」なら続く
- p.323「16」: HP 以上のダメージを受けるときぜつしてトラッシュに置かれる。p.311・p.313: 対戦ポケモンがいなくなったら、
  ベンチから代わりを「すぐに」出す。きぜつしたポケモンは場にいないので 3・4 の対象ではない（SUPPORTED）
- p.325「23」: 同じタイミングのことがらの順番は「そのとき番をおこなっているプレイヤー」が決める（ポケモンチェックは
  どちらの番でもないので、両方のねむりのコインの順番は決まらない。UNRESOLVED）

v0.3a のポケモンチェック（どく・時点・どくのきぜつ）は test_pokemon_check.py。分類は docs/pokemon-check-v0.3b.md。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    EndTurn, EngineError, Phase, PromoteActive, ResolveDecision, TakePrize, UnsupportedError, UseAttack, apply_command,
    check_invariants, state_to_dict,
)
from kyuura_engine.conditions import NORMAL_POISON
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import NO_SPECIAL_CONDITIONS, Paralyzed, SpecialConditions

from tests.helpers import (
    CATERPIE, DIGLETT, GRASS, GROWLITHE, H, PARAS, PONYTA, RATTATA, T, build_test_state, with_coin_results,
)


def full(state):
    return state_to_dict(state, format_version=5)


def kinds(events):
    return [e["kind"] for e in events]


def board(p0, p1, *coins, current_player=0, turn_number=3):
    state = build_test_state([p0, p1], current_player=current_player, turn_number=turn_number)
    return with_coin_results(state, *coins) if coins else state


def end_turn(state):
    start = len(state.log)
    new = apply_command(state, EndTurn(state.current_player))
    return new, [dict(e) for e in new.log[start:]]


def answer_all(state):
    answered = []
    while state.decision is not None:
        d = state.decision
        answered.append((d.kind, d.player))
        state = apply_command(state, ResolveDecision(d.player, d.id, (d.options[0],)))
    return state, answered


def check_events(state, start=0):
    """最後のポケモンチェックから次の番の始まりまでのイベント。"""
    log = [dict(e) for e in state.log[start:]]
    i = max(j for j, e in enumerate(log) if e["kind"] == "pokemon_check")
    end = next((j for j in range(i, len(log)) if log[j]["kind"] == "turn_start"), len(log))
    return log[i:end]


class CheckStepsTest(unittest.TestCase):
    def test_no_conditions_no_coin(self):
        """特殊状態がなければ、ポケモンチェックでは何もせず、乱数も使わない（v0.3a と同じログ）。"""
        state = board({"active": PARAS}, {"active": GROWLITHE})
        fingerprint = rng_fingerprint(state.rng)
        new, events = end_turn(state)
        self.assertEqual(kinds(events), ["end_turn_without_attack", "turn_end", "pokemon_check", "turn_start", "draw"])
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)

    def test_poison_only(self):
        new, events = end_turn(board({"active": PARAS}, {"active": {"card": GROWLITHE, "poison": 10}}))
        self.assertEqual(kinds(check_events(new)), ["pokemon_check", "poison_damage"])

    def test_sleep_coin_is_flipped_by_the_owner_after_either_players_turn(self):
        """ねむり状態のポケモンの持ち主（番のプレイヤーでなくても）がコインを 1 枚投げる（p.323 の 3）。自分の番のあとでも、
        相手の番のあとでも投げる（p.322「ポケモンチェックのたびに」）。"""
        for current_player, owner in ((0, 1), (0, 0), (1, 0), (1, 1)):
            with self.subTest(current_player=current_player, owner=owner):
                specs = [{"active": PARAS}, {"active": GROWLITHE}]
                specs[owner] = {"active": {"card": specs[owner]["active"], "sleep": True}}
                state = board(*specs, T, current_player=current_player, turn_number=3 if current_player == 0 else 4)
                target = state.players[owner].active
                new, _ = end_turn(state)
                events = check_events(new)
                self.assertEqual(kinds(events), ["pokemon_check", "coin_flip", "sleep_check"])
                coin, check = events[1], events[2]
                self.assertEqual({k: coin[k] for k in ("player", "source", "effect", "card", "pokemon_id", "number", "count", "result")},
                                 {"player": owner, "source": "pokemon_check", "effect": "sleep", "card": target.card,
                                  "pokemon_id": target.pokemon_id, "number": 1, "count": 1, "result": "tails"})
                self.assertEqual({k: check[k] for k in ("player", "pokemon", "pokemon_id", "result", "recovered")},
                                 {"player": owner, "pokemon": target.card, "pokemon_id": target.pokemon_id, "result": "tails", "recovered": False})
                self.assertTrue(new.players[owner].active.conditions.asleep)

    def test_heads_recovers(self):
        new, _ = end_turn(board({"active": PARAS}, {"active": {"card": GROWLITHE, "sleep": True}}, H))
        events = check_events(new)
        self.assertEqual(kinds(events), ["pokemon_check", "coin_flip", "sleep_check", "special_conditions_removed"])
        self.assertEqual((events[2]["recovered"], events[3]["conditions"], events[3]["reason"]), (True, ("sleep",), "sleep_coin"))
        self.assertEqual(new.players[1].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_paralysis_only_recovers_on_its_turn_without_a_coin(self):
        """4: 回復する番の終わりのチェックだけで回復する。ほかのチェックでは何もしない。コインは投げない。"""
        state = board({"active": PARAS}, {"active": {"card": GROWLITHE, "paralysis": 3}})  # 4 番の終わりに回復
        fingerprint = rng_fingerprint(state.rng)
        state, _ = end_turn(state)  # 3 番の終わり
        self.assertEqual(kinds(check_events(state)), ["pokemon_check"])
        state, _ = end_turn(state)  # 4 番の終わり
        events = check_events(state)
        self.assertEqual(kinds(events), ["pokemon_check", "special_conditions_removed"])
        self.assertEqual((events[1]["player"], events[1]["conditions"], events[1]["reason"]), (1, ("paralysis",), "paralysis_end"))
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)

    def test_order_poison_then_sleep_then_paralysis(self):
        """2 どく → 3 ねむり → 4 マヒ（p.323）。プレイヤー 0 がどく + ねむり、プレイヤー 1 がどく + マヒ（この番の終わりに回復）。"""
        state = board({"active": {"card": PARAS, "poison": 10, "sleep": True}},
                      {"active": {"card": GROWLITHE, "poison": 10, "paralysis": 2}}, H, current_player=1, turn_number=4)
        new, _ = end_turn(state)
        events = check_events(new)
        self.assertEqual(kinds(events), ["pokemon_check", "poison_damage", "poison_damage", "coin_flip", "sleep_check",
                                         "special_conditions_removed", "special_conditions_removed"])
        self.assertEqual([(e["player"], e["reason"]) for e in events if e["kind"] == "special_conditions_removed"],
                         [(0, "sleep_coin"), (1, "paralysis_end")])
        # ねむり・マヒだけが消え、どくは残る（p.322）
        self.assertEqual([p.active.conditions for p in new.players], [SpecialConditions(poison=NORMAL_POISON)] * 2)
        self.assertEqual([p.active.damage for p in new.players], [10, 10])

    def test_the_check_is_done_once(self):
        """番と番のあいだにポケモンチェックは 1 回だけ。ねむりのコインも 1 匹につき 1 枚だけ（二重に行わない）。"""
        state = board({"active": {"card": PARAS, "sleep": True}}, {"active": GROWLITHE}, T, T)
        new, events = end_turn(state)
        self.assertEqual((kinds(events).count("pokemon_check"), kinds(events).count("coin_flip"), kinds(events).count("draw")), (1, 1, 1))
        self.assertEqual(check_invariants(new), [])


class BothAsleepTest(unittest.TestCase):
    """両方の対戦ポケモンがねむり状態（v0.3b の対応カードでは起こらない。docs/pokemon-check-v0.3b.md 4 章）。

    どちらが先にコインを投げるか（順番を決めるプレイヤーがいるか）が原典で決まらず、投げる順番で乱数の割り当てが変わる。
    推測で順番を決めず、コインを投げる前に止める（UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）。"""

    def test_halts_before_any_coin(self):
        for current_player in (0, 1):
            with self.subTest(current_player=current_player):
                state = board({"active": {"card": PARAS, "sleep": True}}, {"active": {"card": GROWLITHE, "sleep": True}},
                              current_player=current_player, turn_number=3 + current_player)
                fingerprint = rng_fingerprint(state.rng)
                new, events = end_turn(state)
                self.assertEqual(kinds(events)[-3:], ["turn_end", "pokemon_check", "halted"])
                self.assertEqual((new.phase, new.halt.code, new.result), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER", None))
                self.assertNotIn("coin_flip", kinds(events))
                self.assertEqual(rng_fingerprint(new.rng), fingerprint)
                self.assertTrue(all(p.active.conditions.asleep for p in new.players))
                self.assertEqual(check_invariants(new), [])
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(new, EndTurn(1 - current_player))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER")

    def test_poison_damage_is_given_before_the_halt(self):
        """2 のどくのダメージは 3 より前（p.323）。どくできぜつしなければダメージを与えてから、3 で止める。"""
        state = board({"active": {"card": PARAS, "sleep": True, "poison": 10}}, {"active": {"card": GROWLITHE, "sleep": True}})
        new, events = end_turn(state)
        self.assertEqual(kinds(events)[-4:], ["turn_end", "pokemon_check", "poison_damage", "halted"])
        self.assertEqual(new.players[0].active.damage, 10)

    def test_one_knocked_out_by_poison_then_the_other_flips(self):
        """片方がどくできぜつすれば、3 の時点でねむり状態は 1 匹だけになり、順番の問題はない（止めない）。きぜつしたポケモンの
        コインは投げない。代わりに出たポケモンはベンチにいたので特殊状態がない（p.322）。"""
        state = board({"active": {"card": PARAS, "sleep": True}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10, "sleep": True}, "bench": [PONYTA]}, T)
        state, events = end_turn(state)
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assertNotIn("coin_flip", kinds(events))
        state, answered = answer_all(state)
        self.assertEqual(answered, [("take_prize", 0), ("promote_active", 1)])
        events = check_events(state)
        coins = [(e["player"], e["source"]) for e in events if e["kind"] == "coin_flip"]
        self.assertEqual(coins, [(0, "pokemon_check")])
        self.assertEqual((state.players[1].active.conditions, state.phase, state.current_player), (NO_SPECIAL_CONDITIONS, Phase.MAIN, 1))

    def test_double_poison_knock_out_still_halts_before_the_damage_and_coins(self):
        """v0.3a の未解決（両方がどくできぜつ）はそのまま。ねむりがあっても、ダメージ・コインの前に止める。"""
        state = board({"active": {"card": RATTATA, "damage": 20, "poison": 10, "sleep": True}, "bench": [PONYTA]},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10, "sleep": True}, "bench": [PONYTA]})
        fingerprint = rng_fingerprint(state.rng)
        new, events = end_turn(state)
        self.assertEqual((new.phase, new.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"))
        self.assertEqual(kinds(events)[-3:], ["turn_end", "pokemon_check", "halted"])
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)


class PoisonKnockOutAndStepsTest(unittest.TestCase):
    """2 のどくのきぜつ → サイド → 判定 → 交代（「すぐに」p.311・p.313）→ 3 → 4 → 次の番。"""

    def test_knocked_out_asleep_pokemon_gets_no_coin(self):
        state = board({"active": GROWLITHE}, {"active": {"card": RATTATA, "damage": 20, "poison": 10, "sleep": True}, "bench": [PONYTA]})
        fingerprint = rng_fingerprint(state.rng)
        state, _ = end_turn(state)
        state, _ = answer_all(state)
        self.assertNotIn("coin_flip", kinds(check_events(state)))
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)

    def test_the_other_players_sleep_coin_comes_after_the_promotion(self):
        """交代が終わってから 3 のコインを投げる（交代するプレイヤーは結果を見ずに選ぶ）。番のプレイヤー（0）のねむり。"""
        state = board({"active": {"card": PARAS, "sleep": True}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA, DIGLETT]}, H)
        state, events = end_turn(state)
        self.assertEqual(kinds(events)[-4:], ["turn_end", "pokemon_check", "poison_damage", "knock_out"])
        self.assertEqual((state.decision.kind, state.decision.context_value("then")), ("take_prize", "next_turn"))
        state = apply_command(state, TakePrize(0, 0))
        self.assertNotIn("coin_flip", kinds([dict(e) for e in state.log]))
        state = apply_command(state, PromoteActive(1, state.players[1].bench[1].card))
        events = check_events(state)
        self.assertEqual(kinds(events)[-5:], ["take_prize", "promote_active", "coin_flip", "sleep_check", "special_conditions_removed"])
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 1, 4))
        log = [dict(e) for e in state.log]
        self.assertEqual(kinds(log).count("pokemon_check"), 1)
        self.assertEqual(kinds(log)[-2:], ["turn_start", "draw"])

    def test_paralysis_recovery_after_the_promotion(self):
        """4 のマヒの回復も、交代のあと（3 のあと）。プレイヤー 0 のマヒは 3 番の終わりに回復する（2 番にマヒ状態）。"""
        state = board({"active": {"card": PARAS, "paralysis": 2}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        self.assertTrue(state.players[0].active.conditions.paralyzed)  # まだ（決定を待っている）
        self.assertEqual(check_invariants(state), [])
        state, _ = answer_all(state)
        events = check_events(state)
        self.assertEqual(kinds(events)[-3:], ["take_prize", "promote_active", "special_conditions_removed"])
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_game_over_in_step_2_skips_the_rest(self):
        """どくのきぜつで勝敗が決まったら、対戦は終わる。3・4 はしない（コインも投げない。マヒも残ったまま）。"""
        for name, p1 in (("最後のサイド", {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]}),
                         ("ベンチなし", {"active": {"card": RATTATA, "damage": 20, "poison": 10}})):
            with self.subTest(name):
                p0 = {"active": {"card": PARAS, "sleep": True}, "prizes": 1 if name == "最後のサイド" else 6}
                state = board(p0, p1)
                fingerprint = rng_fingerprint(state.rng)
                state, _ = end_turn(state)
                state, _ = answer_all(state)
                self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 0))
                self.assertNotIn("coin_flip", kinds([dict(e) for e in state.log]))
                self.assertEqual(rng_fingerprint(state.rng), fingerprint)
                self.assertTrue(state.players[0].active.conditions.asleep)
                self.assertEqual(check_invariants(state), [])

    def test_paralysis_left_when_the_game_ends_in_step_2(self):
        state = board({"active": {"card": PARAS, "paralysis": 2}}, {"active": {"card": RATTATA, "damage": 20, "poison": 10}})
        state, _ = end_turn(state)
        state, _ = answer_all(state)
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.players[0].active.conditions.exclusive, Paralyzed(turn=2))
        self.assertEqual(check_invariants(state), [])

    def test_rejections_during_the_check_do_not_flip_coins(self):
        """ポケモンチェックの中の決定を待つ間の不正な操作・決定は、状態も乱数も変えない（コインを先に投げない）。"""
        state = board({"active": {"card": PARAS, "sleep": True, "energy": [GRASS, GRASS]}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        d = state.decision
        for command in (EndTurn(0), EndTurn(1), UseAttack(0, 0), ResolveDecision(1, d.id, (0,)), ResolveDecision(0, d.id + 1, (0,)),
                        ResolveDecision(0, d.id, (99,))):
            with self.subTest(command=command):
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                with self.assertRaises(EngineError):
                    apply_command(state, command)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_copies_during_the_check_give_the_same_coin(self):
        state = board({"active": {"card": PARAS, "sleep": True}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        results = [full(answer_all(copied)[0]) for copied in (state, state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state)))]
        self.assertTrue(all(r == results[0] for r in results))
        # 決定のあとで投げるコインは、決定の前の乱数の続き（決定・サイド・交代は乱数を使わない）
        expected = copy_rng(state.rng)
        final, _ = answer_all(state)
        coin = next(e for e in check_events(final) if e["kind"] == "coin_flip")
        self.assertEqual(coin["result"], "heads" if expected.getrandbits(1) else "tails")

    def test_formats_during_the_check(self):
        state = board({"active": {"card": PARAS, "sleep": True}},
                      {"active": {"card": RATTATA, "damage": 20, "poison": 10}, "bench": [PONYTA]})
        state, _ = end_turn(state)
        data = full(state)
        self.assertEqual(data["decision"]["context"]["then"], "next_turn")
        self.assertEqual(data["players"][0]["active"]["special_conditions"], {"sleep": {}})
        for version in (1, 2, 3, 4):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)  # ねむりは形式 5 だけ（形式 1 は決定の続きも表せない）


class AttackThenCheckTest(unittest.TestCase):
    """ワザのコインとポケモンチェックのコインの乱数の順番（ワザ → チェック）。"""

    def test_attack_coin_then_check_coin(self):
        """ねむりのガーディに、いとをはく（「うら」でマヒにしない）→ ポケモンチェックでねむりのコイン（「おもて」で回復）。"""
        state = board({"active": {"card": CATERPIE, "energy": [GRASS]}}, {"active": {"card": GROWLITHE, "sleep": True}}, T, H)
        start = len(state.log)
        new = apply_command(state, UseAttack(0, 0))
        coins = [(e["source"], e["effect"], e["player"], e["result"]) for e in new.log[start:] if e["kind"] == "coin_flip"]
        self.assertEqual(coins, [("attack", "PMCG1-002#0", 0, "tails"), ("pokemon_check", "sleep", 1, "heads")])
        expected = copy_rng(state.rng)
        expected.getrandbits(1)
        expected.getrandbits(1)
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(expected))

    def test_heads_paralysis_replaces_sleep_and_no_check_coin(self):
        state = board({"active": {"card": CATERPIE, "energy": [GRASS]}}, {"active": {"card": GROWLITHE, "sleep": True}}, H)
        start = len(state.log)
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual([e["source"] for e in new.log[start:] if e["kind"] == "coin_flip"], ["attack"])
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=Paralyzed(turn=3)))

    def test_spore_then_check_coin_in_the_same_turn(self):
        """キノコのほうしでねむりにした番の終わりのポケモンチェックで、もうコインを投げる（p.322「ポケモンチェックのたびに」）。"""
        state = board({"active": {"card": PARAS, "energy": [GRASS, GRASS]}}, {"active": GROWLITHE}, H)
        new = apply_command(state, UseAttack(0, 1))
        self.assertEqual(new.players[1].active.conditions, NO_SPECIAL_CONDITIONS)
        self.assertEqual([e["kind"] for e in check_events(new)], ["pokemon_check", "coin_flip", "sleep_check", "special_conditions_removed"])
        self.assertEqual(new.players[0].active.conditions, NO_SPECIAL_CONDITIONS)  # ワザを使ったパラスは特殊状態ではない


if __name__ == "__main__":
    unittest.main()
