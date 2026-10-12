"""ねむり・マヒ（v0.3b）: 状態の付与・重複と上書き・ワザとにげるの制限・ポケモンいれかえ・原子性・状態の保存。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）:

- p.309「バトル場にいるポケモンのワザを使う」: 手順 1「ワザを使うことができなくなる効果を受けているかどうか、チェック
  します」、手順 2 必要なエネルギー、手順 3 の「「ねむり」や「マヒ」状態になっていたり…するポケモンは、ワザの使用を
  宣言できません」
- p.311: 「バトル場にいるポケモンがねむり状態またはマヒ状態のとき、そのポケモンは「にげる」を宣言することができません」。
  「ベンチに戻ったら、そのポケモンの「どく」「ねむり」「マヒ」「こんらん」状態…は、すべて消えてなくなります」
- p.322「10 ポケモンの特殊状態」: 特殊状態になるのはバトル場のポケモンだけ。特殊状態でもエネルギーカードをつけられる。
  「2. ねむり状態」ワザを使えない・にげるを宣言できない・ポケモンチェックのたびに持ち主がコインを投げ「おもて」なら
  回復・二重にならない。「3. マヒ状態」ワザを使えない・にげるを宣言できない・「次の自分（そのポケモンの持ち主）の番」の
  終わりのポケモンチェックで自動的に回復・二重にならない。「特殊状態の重複」「ねむり」「マヒ」「こんらん」は重複しない
  （マヒ状態のポケモンがねむり状態になったら、マヒから自動的に回復してねむり状態）。どくはほかの特殊状態と重複する
- p.323 のポケモンチェックの 3・4（ポケモンチェックそのものは test_pokemon_check_v0_3b.py）
- p.325「21 ポケモンの入れ替え」: 「にげる」がおこなえない状態のポケモンでも、「そのポケモンを入れ替える」と指示された
  ときは、入れ替えをおこなう

カードそのもの（キャタピー p.17・パラス p.38）は test_caterpie_paras.py、正式な対戦開始からは
test_sleep_paralysis_games.py。分類（CONFIRMED・SUPPORTED・UNRESOLVED）は docs/sleep-paralysis-v0.3b.md。
"""

import copy
import dataclasses
import json
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, Phase, PlayBasicToBench, PlayTrainer, ResolveDecision, Retreat, UnsupportedError,
    UseAttack, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.conditions import (
    NORMAL_POISON, paralysis_problem, paralysis_recovery_turn, paralyze, poison, put_to_sleep,
)
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey
from kyuura_engine.rng import copy_rng, rng_fingerprint, rng_from_json, rng_state_to_json
from kyuura_engine.state import ASLEEP, NO_SPECIAL_CONDITIONS, Asleep, Paralyzed, Poison, SpecialConditions

from tests.helpers import (
    BILL, CATERPIE, DODUO, FIRE, GRASS, GROWLITHE, H, PARAS, PONYTA, RATTATA, SWITCH, T, WEEDLE,
    build_test_state, with_coin_results,
)

STRING_SHOT = 0  # キャタピーの「いとをはく」
SCRATCH, SPORE = 0, 1  # パラスの「ひっかく」「キノコのほうし」
POISON_STING = 0  # ビードルの「どくばり」


def full(state):
    return state_to_dict(state, format_version=5)


def kinds(events):
    return [e["kind"] for e in events]


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def board(attacker, defender=GROWLITHE, *sides, energy=(GRASS, GRASS), defender_spec=None, bench=(PONYTA,),
          their_bench=(RATTATA,), hand_cards=(), their_hand=(), their_energy=()):
    """プレイヤー 0（3 番。先攻）の対戦ポケモン ``attacker`` と、プレイヤー 1 の対戦ポケモン ``defender``。"""
    spec = {"card": defender, "energy": list(their_energy), **(defender_spec or {})}
    state = build_test_state([
        {"active": {"card": attacker, "energy": list(energy)}, "bench": list(bench), "hand": list(hand_cards)},
        {"active": spec, "bench": list(their_bench), "hand": list(their_hand)},
    ])
    return with_coin_results(state, *sides) if sides else state


def restricted_board(condition, *, hand_cards=(), bench=(PONYTA,), energy=(GRASS, GRASS)):
    """プレイヤー 0（番）のパラスが ``condition``（"sleep" か "paralysis"）。ワザ・にげるの制限を確かめる盤面。

    マヒは前の番（2 番、相手の番）にマヒ状態になった（今の番 3 番の終わりに回復する）。"""
    spec = {"card": PARAS, "energy": list(energy)}
    spec.update({"sleep": True} if condition == "sleep" else {"paralysis": 2})
    return build_test_state([
        {"active": spec, "bench": list(bench), "hand": list(hand_cards)},
        {"active": GROWLITHE, "bench": [RATTATA]},
    ])


def use(state, player, index):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, index))
    return new, [dict(e) for e in new.log[start:]]


def assert_unchanged_rejection(test, state, command, code):
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(EngineError) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


# ---------------------------------------------------------------- ねむり（11.1）


class SleepTest(unittest.TestCase):
    def test_spore_puts_the_defending_pokemon_to_sleep(self):
        """キノコのほうし（p.38）: ダメージはなく、相手の対戦ポケモンをねむり状態にする。番が終わり、ポケモンチェックで
        ねむり状態のポケモンの持ち主（プレイヤー 1）がコインを投げる（p.323 の 3）。「うら」なら続く（p.322）。"""
        state = board(PARAS, GROWLITHE, T)
        target = state.players[1].active
        new, events = use(state, 0, SPORE)
        self.assertEqual(kinds(events)[:6], ["attack", "special_condition", "turn_end", "pokemon_check", "coin_flip", "sleep_check"])
        self.assertNotIn("damage", kinds(events))
        applied = events[1]
        self.assertEqual({k: applied[k] for k in ("player", "pokemon", "pokemon_id", "condition", "effect")},
                         {"player": 1, "pokemon": target.card, "pokemon_id": target.pokemon_id, "condition": "sleep", "effect": "PMCG2-003#1"})
        self.assertNotIn("already", applied)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=ASLEEP))
        self.assertEqual(new.players[1].active.damage, 0)
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 1, 4))
        self.assertEqual(check_invariants(new), [])

    def test_asleep_pokemon_cannot_attack(self):
        """p.309 手順 1・3、p.322: ねむり状態のポケモンはワザを使えない。コイン・ダメージ・番の終わりの前に拒否する
        （コインを投げるワザでも乱数は進まない。必要なエネルギーが足りていても拒否する）。"""
        for attacker, index, energy in ((PARAS, SCRATCH, (GRASS, GRASS)), (PARAS, SPORE, (GRASS, GRASS)), (CATERPIE, STRING_SHOT, (GRASS,)),
                                        (DODUO, 0, (FIRE,))):
            with self.subTest(attacker=attacker, index=index):
                state = build_test_state([
                    {"active": {"card": attacker, "energy": list(energy), "sleep": True}, "bench": [PONYTA]},
                    {"active": GROWLITHE},
                ])
                assert_unchanged_rejection(self, state, UseAttack(0, index), "POKEMON_ASLEEP")

    def test_asleep_check_comes_before_the_energy_check(self):
        """p.309 の手順: 1 ワザを使えなくなる効果 → 2 必要なエネルギー。エネルギーが足りなくても、ねむりで拒否する。"""
        state = restricted_board("sleep", energy=())
        assert_unchanged_rejection(self, state, UseAttack(0, SCRATCH), "POKEMON_ASLEEP")
        assert_unchanged_rejection(self, state, UseAttack(0, 5), "INVALID_ATTACK")  # ワザの位置の誤りはコマンドの誤り

    def test_asleep_pokemon_cannot_retreat(self):
        """p.311・p.322: にげるを宣言できない。エネルギーをトラッシュせず、ポケモンも動かない。"""
        state = restricted_board("sleep")
        active = state.players[0].active
        assert_unchanged_rejection(self, state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card), "POKEMON_ASLEEP")

    def test_switch_moves_an_asleep_pokemon(self):
        """p.325: にげるを宣言できないポケモンでも、ポケモンいれかえでは入れ替える。ベンチに戻ったらねむりは消える（p.311・p.322）。"""
        state = restricted_board("sleep", hand_cards=[SWITCH])
        paras = state.players[0].active
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        start = len(state.log)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        events = [dict(e) for e in state.log[start:]]
        removed = next(e for e in events if e["kind"] == "special_conditions_removed")
        self.assertEqual((removed["pokemon_id"], removed["conditions"], removed["reason"]), (paras.pokemon_id, ("sleep",), "switch"))
        benched = next(p for p in state.players[0].bench if p.pokemon_id == paras.pokemon_id)
        self.assertEqual((benched.conditions, len(benched.energy)), (NO_SPECIAL_CONDITIONS, 2))
        # 入れ替わって出てきたポケモンはワザを使える（ポニータのけりとばすには無色 2 が要るので、ここでは番を終える）
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)
        self.assertEqual(check_invariants(state), [])

    def test_other_actions_are_allowed_while_asleep(self):
        """p.322「特殊状態になっていても、そのポケモンにエネルギーカードをつけたり…することはできます」。制限はワザとにげるだけ。"""
        state = restricted_board("sleep", hand_cards=[GRASS, RATTATA, BILL])
        state = apply_command(state, AttachEnergy(0, hand(state, 0, GRASS)[0], state.players[0].active.card))
        state = apply_command(state, PlayBasicToBench(0, hand(state, 0, RATTATA)[0]))
        state = apply_command(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
        self.assertEqual(len(state.players[0].active.energy), 3)
        self.assertTrue(state.players[0].active.conditions.asleep)
        state = apply_command(with_coin_results(state, T), EndTurn(0))  # ワザを使わずに番を終えられる（p.309）
        self.assertEqual(state.current_player, 1)

    def test_sleep_persists_across_checks_until_heads(self):
        """ねむり状態は「うら」のあいだ続き、ポケモンチェックのたび（どちらのプレイヤーの番のあとでも）に 1 枚投げる（p.322）。"""
        state = build_test_state([{"active": {"card": PARAS, "sleep": True}, "bench": [PONYTA]}, {"active": GROWLITHE}])
        state = with_coin_results(state, T, T, H)
        flips = []
        for _ in range(3):
            start = len(state.log)
            state = apply_command(state, EndTurn(state.current_player))
            flips += [(e["player"], e["result"]) for e in state.log[start:] if e["kind"] == "coin_flip"]
        self.assertEqual(flips, [(0, "tails"), (0, "tails"), (0, "heads")])
        self.assertEqual(state.players[0].active.conditions, NO_SPECIAL_CONDITIONS)
        start = len(state.log)
        state = apply_command(state, EndTurn(state.current_player))
        self.assertNotIn("coin_flip", [e["kind"] for e in state.log[start:]])  # 回復したら、もう投げない

    def test_already_asleep(self):
        """p.322「ねむり状態のポケモンが再びねむり状態になる効果を受けても、二重のねむり状態になるわけではありません」。
        状態は変わらず、ポケモンチェックのコインは 1 枚だけ。"""
        state = board(PARAS, GROWLITHE, T, defender_spec={"sleep": True})
        new, events = use(state, 0, SPORE)
        applied = next(e for e in events if e["kind"] == "special_condition")
        self.assertTrue(applied["already"])
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=ASLEEP))
        self.assertEqual(kinds(events).count("coin_flip"), 1)

    def test_only_the_active_pokemon(self):
        state = board(PARAS)
        with self.assertRaises(RuntimeError):
            put_to_sleep(state, 1, state.players[1].bench[0], effect="test")
        with self.assertRaises(RuntimeError):
            paralyze(state, 1, state.players[1].bench[0], effect="test")


# ---------------------------------------------------------------- マヒ（11.2）


class ParalysisTest(unittest.TestCase):
    def paralyzed_at_turn_3(self):
        """3 番（プレイヤー 0）にキャタピーのいとをはく（「おもて」）で、プレイヤー 1 のガーディをマヒ状態にした直後。"""
        state = board(CATERPIE, GROWLITHE, H, energy=(GRASS,))
        return use(state, 0, STRING_SHOT)

    def test_paralysis_is_applied_with_its_turn(self):
        """マヒ状態になった番（3）を持つ。回復するのは「次の自分（持ち主）の番」= 4 番の終わり（p.322・p.323 の 4）。"""
        new, events = self.paralyzed_at_turn_3()
        applied = next(e for e in events if e["kind"] == "special_condition")
        self.assertEqual({k: applied[k] for k in ("player", "condition", "paralyzed_turn", "recovery_turn", "effect")},
                         {"player": 1, "condition": "paralysis", "paralyzed_turn": 3, "recovery_turn": 4, "effect": "PMCG1-002#0"})
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=Paralyzed(turn=3)))

    def test_not_recovered_at_the_end_of_the_turn_it_was_paralyzed(self):
        """マヒ状態になった番（相手の番）の終わりのポケモンチェックでは回復しない（コインも投げない）。"""
        new, events = self.paralyzed_at_turn_3()
        check = kinds(events).index("pokemon_check")
        self.assertEqual(kinds(events)[check:check + 2], ["pokemon_check", "turn_start"])
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        self.assertEqual((new.turn_number, new.current_player), (4, 1))

    def test_owner_cannot_attack_or_retreat_during_the_next_turn(self):
        """持ち主の次の番（4 番）のあいだはマヒしている（「1回休みのような感じ」p.322）。ワザもにげるも拒否する。"""
        state, _ = self.paralyzed_at_turn_3()
        # ガーディのエネルギーは 0 枚。ワザの確認は手順 1（マヒ）が先（p.309）
        assert_unchanged_rejection(self, state, UseAttack(1, 0), "POKEMON_PARALYZED")
        rattata = state.players[1].bench[0]
        assert_unchanged_rejection(self, state, Retreat(1, (), rattata.card), "POKEMON_PARALYZED")

    def test_recovers_automatically_at_the_end_of_the_owners_next_turn(self):
        """ワザを使わずに番を終えても、4 番の終わりのポケモンチェックで自動的に回復する（コインは投げない。p.323 の 4）。"""
        state, _ = self.paralyzed_at_turn_3()
        fingerprint = rng_fingerprint(state.rng)
        start = len(state.log)
        state = apply_command(state, EndTurn(1))
        events = [dict(e) for e in state.log[start:]]
        self.assertEqual(kinds(events)[:5], ["end_turn_without_attack", "turn_end", "pokemon_check", "special_conditions_removed", "turn_start"])
        removed = events[3]
        self.assertEqual((removed["player"], removed["conditions"], removed["reason"]), (1, ("paralysis",), "paralysis_end"))
        self.assertEqual(state.players[1].active.conditions, NO_SPECIAL_CONDITIONS)
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)
        self.assertEqual((state.turn_number, state.current_player), (5, 0))

    def test_recovery_turn_counts_the_owners_turns(self):
        """「次の自分（持ち主）の番」は番の数 + 1 とは限らない（p.323 の 4）。持ち主の番にマヒ状態になったら 2 つ後の番。
        先攻がプレイヤー 1 でも、番の持ち主で数える。"""
        state = board(CATERPIE)
        self.assertEqual([paralysis_recovery_turn(state, 1, t) for t in (1, 2, 3, 4)], [2, 4, 4, 6])
        self.assertEqual([paralysis_recovery_turn(state, 0, t) for t in (1, 2, 3, 4)], [3, 3, 5, 5])
        state.first_player = 1
        self.assertEqual([paralysis_recovery_turn(state, 1, t) for t in (1, 2, 3)], [3, 3, 5])

    def test_paralysis_received_during_the_owners_own_turn(self):
        """持ち主の番（3 番）にマヒ状態になったら（v0.3b の対応カードにはない。規定の数え方を確かめる）、3 番・4 番の終わりでは
        回復せず、次の自分の番（5 番）の終わりで回復する。"""
        state = build_test_state([{"active": {"card": PARAS, "energy": [GRASS]}, "bench": [PONYTA]}, {"active": GROWLITHE}])
        paralyze(state, 0, state.players[0].active, effect="test")
        self.assertEqual(state.players[0].active.conditions.exclusive, Paralyzed(turn=3))
        recovered_after = []
        for _ in range(3):
            turn = state.turn_number
            state = apply_command(state, EndTurn(state.current_player))
            if not state.players[0].active.conditions.paralyzed:
                recovered_after.append(turn)
                break
        self.assertEqual(recovered_after, [5])

    def test_switch_moves_a_paralyzed_pokemon(self):
        state = restricted_board("paralysis", hand_cards=[SWITCH])
        paras = state.players[0].active
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        start = len(state.log)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        removed = next(dict(e) for e in state.log[start:] if e["kind"] == "special_conditions_removed")
        self.assertEqual((removed["pokemon_id"], removed["conditions"], removed["reason"]), (paras.pokemon_id, ("paralysis",), "switch"))
        start = len(state.log)
        state = apply_command(state, EndTurn(0))  # ベンチのポケモンのマヒはもうない。回復の処理もない
        self.assertNotIn("special_conditions_removed", [e["kind"] for e in state.log[start:]])

    def test_paralyzed_pokemon_cannot_attack_or_retreat(self):
        state = restricted_board("paralysis")
        for index in (SCRATCH, SPORE):
            assert_unchanged_rejection(self, state, UseAttack(0, index), "POKEMON_PARALYZED")
        active = state.players[0].active
        assert_unchanged_rejection(self, state, Retreat(0, (active.energy[0],), state.players[0].bench[0].card), "POKEMON_PARALYZED")

    def test_already_paralyzed_with_the_same_recovery_turn(self):
        """p.322「二重のマヒ状態になるわけではありません」。回復する番が変わらない場合は、状態を変えない（ログに already）。"""
        state = board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"paralysis": 3})
        new, events = use(state, 0, STRING_SHOT)
        applied = next(e for e in events if e["kind"] == "special_condition")
        self.assertEqual((applied["already"], applied["paralyzed_turn"], applied["recovery_turn"]), (True, 3, 4))
        self.assertEqual(new.players[1].active.conditions.exclusive, Paralyzed(turn=3))
        # 2 番（持ち主の番）にマヒ状態になっていても、回復する番は同じ 4 番なので扱える（もとの番を残す）
        state = board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"paralysis": 2})
        new, _ = use(state, 0, STRING_SHOT)
        self.assertEqual(new.players[1].active.conditions.exclusive, Paralyzed(turn=2))

    def test_reparalysis_with_a_different_recovery_turn_is_unresolved(self):
        """回復する番が最初の番とあとの番で違う場合は、原典で決められない（UNRESOLVED）。成功を仮定せず止める。

        2 番（相手の番）にマヒ状態になり 3 番の終わりに回復するポケモンが、3 番（持ち主の番）に再びマヒを受けたら、あとの番で
        数えると 5 番になる。v0.3b の対応カード（相手だけをマヒにする）ではこの状態にならないので、処理を直接呼んで確かめる。"""
        state = restricted_board("paralysis")
        paras = state.players[0].active
        problem = paralysis_problem(state, 0, paras)
        self.assertIsInstance(problem, UnsupportedError)
        self.assertEqual(problem.code, "UNRESOLVED_REPARALYSIS_RECOVERY_TURN")
        log_length = len(state.log)
        with self.assertRaises(UnsupportedError):
            paralyze(state, 0, paras, effect="test")
        self.assertEqual((paras.conditions.exclusive, len(state.log)), (Paralyzed(turn=2), log_length))
        self.assertIsNone(paralysis_problem(state, 1, state.players[1].active))  # マヒでなければ問題はない


# ---------------------------------------------------------------- 重複と上書き（11.3）


class OverlapTest(unittest.TestCase):
    """p.322「特殊状態の重複」: ねむり・マヒ・こんらんは重複しない。どくはほかの特殊状態と重複する。"""

    def test_paralysis_replaced_by_sleep(self):
        """CONFIRMED（p.322 の例）: マヒ状態のポケモンがねむり状態になったら、マヒから自動的に回復してねむり状態になる。"""
        state = board(PARAS, GROWLITHE, T, defender_spec={"paralysis": 3})
        target = state.players[1].active
        new, events = use(state, 0, SPORE)
        self.assertEqual(kinds(events)[:3], ["attack", "special_conditions_removed", "special_condition"])
        removed = events[1]
        self.assertEqual((removed["pokemon_id"], removed["conditions"], removed["reason"]), (target.pokemon_id, ("paralysis",), "replaced"))
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=ASLEEP))
        # マヒの回復（4 番の終わり）はもうない。ねむりのコインだけ（3 番の終わりに 1 枚）
        self.assertEqual(kinds(events).count("coin_flip"), 1)

    def test_sleep_replaced_by_paralysis(self):
        """SUPPORTED（p.322 の「重複することはありません」と、上の例の扱い）: ねむり状態のポケモンがマヒ状態になったら、ねむりは
        消えてマヒ状態になる。そのポケモンチェックでねむりのコインは投げない。"""
        state = board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"sleep": True})
        new, events = use(state, 0, STRING_SHOT)
        self.assertEqual(kinds(events)[:5], ["attack", "damage", "coin_flip", "special_conditions_removed", "special_condition"])
        self.assertEqual((events[3]["conditions"], events[3]["reason"]), (("sleep",), "replaced"))
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(exclusive=Paralyzed(turn=3)))
        self.assertEqual(kinds(events).count("coin_flip"), 1)  # いとをはくのコインだけ
        self.assertNotIn("sleep_check", kinds(events))

    def test_tails_keeps_the_previous_condition(self):
        """いとをはくが「うら」なら、マヒにしない。もとのねむりはそのまま（ポケモンチェックでねむりのコインを投げる）。"""
        state = board(CATERPIE, GROWLITHE, T, H, energy=(GRASS,), defender_spec={"sleep": True})
        new, events = use(state, 0, STRING_SHOT)
        self.assertNotIn("special_conditions_removed", kinds(events)[:4])
        self.assertEqual([e["source"] for e in events if e["kind"] == "coin_flip"], ["attack", "pokemon_check"])
        self.assertEqual(new.players[1].active.conditions, NO_SPECIAL_CONDITIONS)  # ポケモンチェックの「おもて」で回復

    def test_poison_coexists_with_sleep_and_paralysis(self):
        """どくはほかの特殊状態と重複する（p.322）。ねむり・マヒになっても、どくは残る（ダメージも変わらない）。"""
        new, _ = use(board(PARAS, GROWLITHE, T, defender_spec={"poison": 10}), 0, SPORE)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=ASLEEP))
        new, _ = use(board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"poison": 10}), 0, STRING_SHOT)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=Paralyzed(turn=3)))

    def test_poison_added_to_sleep_or_paralysis(self):
        """ねむり・マヒ状態のポケモンがどく状態になっても、ねむり・マヒは残る（p.322）。"""
        for spec, exclusive in (({"sleep": True}, ASLEEP), ({"paralysis": 3}, Paralyzed(turn=3))):
            with self.subTest(spec=spec):
                state = board(WEEDLE, GROWLITHE, H, T, energy=(GRASS,), defender_spec=spec)
                new, _ = use(state, 0, POISON_STING)
                self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=exclusive))

    def test_replacing_keeps_the_poison(self):
        """マヒ → ねむり・ねむり → マヒでも、どくはそのまま。"""
        new, _ = use(board(PARAS, GROWLITHE, T, defender_spec={"poison": 10, "paralysis": 3}), 0, SPORE)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=ASLEEP))
        new, _ = use(board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"poison": 10, "sleep": True}), 0, STRING_SHOT)
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=Paralyzed(turn=3)))

    def test_only_sleep_or_paralysis_is_removed_on_recovery(self):
        """ねむりの回復（コイン）・マヒの回復（期限）で消えるのは、その状態だけ。どくは残り、ダメージも続く。"""
        state = board(PARAS, GROWLITHE, H, defender_spec={"poison": 10})
        new, events = use(state, 0, SPORE)
        removed = next(e for e in events if e["kind"] == "special_conditions_removed")
        self.assertEqual((removed["conditions"], removed["reason"]), (("sleep",), "sleep_coin"))
        self.assertEqual(new.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON))
        state, _ = use(board(CATERPIE, GROWLITHE, H, energy=(GRASS,), defender_spec={"poison": 10}), 0, STRING_SHOT)
        state = apply_command(state, EndTurn(1))
        self.assertEqual(state.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON))
        self.assertEqual(state.players[1].active.damage, 30)  # いとをはく 10 + どく 10 × 2

    def test_leaving_the_active_spot_removes_everything(self):
        """ベンチに戻ったら、どくもねむり・マヒもすべて消える（p.311・p.322）。にげるはできないので、ポケモンいれかえで。"""
        state = build_test_state([
            {"active": {"card": PARAS, "energy": [GRASS], "poison": 10, "sleep": True}, "bench": [PONYTA], "hand": [SWITCH]},
            {"active": GROWLITHE},
        ])
        paras = state.players[0].active
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        start = len(state.log)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        removed = next(dict(e) for e in state.log[start:] if e["kind"] == "special_conditions_removed")
        self.assertEqual((removed["pokemon_id"], removed["conditions"]), (paras.pokemon_id, ("poison", "sleep")))

    def test_poisoned_pokemon_can_still_retreat_unless_asleep_or_paralyzed(self):
        """どくだけならにげられる（p.311）。どく + ねむりはにげられない（ねむりの制限）。"""
        poisoned = build_test_state([{"active": {"card": PARAS, "energy": [GRASS], "poison": 10}, "bench": [PONYTA]}, {"active": GROWLITHE}])
        apply_command(poisoned, Retreat(0, tuple(poisoned.players[0].active.energy), poisoned.players[0].bench[0].card))
        both = build_test_state([{"active": {"card": PARAS, "energy": [GRASS], "poison": 10, "sleep": True}, "bench": [PONYTA]},
                                 {"active": GROWLITHE}])
        assert_unchanged_rejection(self, both, Retreat(0, tuple(both.players[0].active.energy), both.players[0].bench[0].card), "POKEMON_ASLEEP")


# ---------------------------------------------------------------- 原子性（11.6）


class _CoinThenFailEffect(AttackEffect):
    """テスト専用: コインを投げ、相手をねむりにしてから、内部の例外を起こすワザ（apply_command の原子性を確かめる）。"""

    implementation_id = "test_coin_then_fail"

    def resolve(self, state, use):
        from kyuura_engine.coins import flip_coins

        flip_coins(state, use.player, 1, source="attack", effect=str(use.key), card=state.players[use.player].active.card)
        put_to_sleep(state, 1 - use.player, state.players[1 - use.player].active, effect=str(use.key))
        raise RuntimeError("テスト専用の内部例外")


class AtomicityTest(unittest.TestCase):
    def test_internal_error_after_the_coin_leaves_the_input_unchanged(self):
        effects = DEFAULT_EFFECTS.with_attacks("test-coin-then-fail", {AttackKey(RATTATA, 0): AttackEntry(_CoinThenFailEffect(), "かみつく")})
        state = build_test_state([{"active": {"card": RATTATA, "energy": [FIRE]}}, {"active": GROWLITHE}], effects=effects)
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(RuntimeError):
            apply_command(state, UseAttack(0, 0))
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertEqual(state.players[1].active.conditions, NO_SPECIAL_CONDITIONS)

    def test_terminal_states_refuse_commands(self):
        """終わった対戦・止めた対戦（両方がねむりのポケモンチェック。test_pokemon_check_v0_3b.py）では、どの操作も受け付けない。"""
        state = build_test_state([{"active": {"card": PARAS, "sleep": True}}, {"active": {"card": GROWLITHE, "sleep": True}}])
        halted = apply_command(state, EndTurn(0))
        self.assertEqual(halted.phase, Phase.HALTED)
        for command in (EndTurn(1), UseAttack(1, 0), EndTurn(0)):
            assert_unchanged_rejection(self, halted, command, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER")


# ---------------------------------------------------------------- 状態の複製・書き出し・不変条件


class StateTest(unittest.TestCase):
    def combined(self):
        """プレイヤー 1 がどく + マヒ（3 番から）、プレイヤー 0 がねむり（盤面を直接作る）。"""
        return build_test_state([
            {"active": {"card": PARAS, "energy": [GRASS], "sleep": True}, "bench": [PONYTA]},
            {"active": {"card": GROWLITHE, "poison": 10, "paralysis": 3}, "bench": [RATTATA]},
        ])

    def test_format_5(self):
        data = full(self.combined())
        self.assertEqual(data["players"][0]["active"]["special_conditions"], {"sleep": {}})
        self.assertEqual(data["players"][1]["active"]["special_conditions"], {"poison": {"damage": 10}, "paralysis": {"turn": 3}})
        self.assertEqual([b["special_conditions"] for p in data["players"] for b in p["bench"]], [{}, {}])
        json.dumps(data)

    def test_older_formats_refuse_sleep_and_paralysis(self):
        for spec in ({"sleep": True}, {"paralysis": 3}):
            state = build_test_state([{"active": PARAS}, {"active": {"card": GROWLITHE, **spec}}])
            for version in (1, 2, 3, 4):
                with self.subTest(spec=spec, version=version), self.assertRaises(ValueError):
                    state_to_dict(state, format_version=version)

    def test_clone_deepcopy_pickle_and_rng_json(self):
        """複製・deepcopy・pickle・乱数の JSON 復元のどれでも、同じ操作で同じ結果（ねむりのコインも同じ）。"""
        state = self.combined()
        expected = apply_command(state, EndTurn(0))
        copies = [state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))]
        restored = state.clone()
        restored.rng = rng_from_json(json.loads(json.dumps(rng_state_to_json(state.rng))))
        copies.append(restored)
        for copied in copies:
            with self.subTest(copy=copies.index(copied)):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(full(apply_command(copied, EndTurn(0))), full(expected))
                copied.players[1].active.conditions = NO_SPECIAL_CONDITIONS
                self.assertTrue(state.players[1].active.conditions.paralyzed)

    def test_conditions_are_frozen_values(self):
        conditions = SpecialConditions(poison=Poison(10), exclusive=Paralyzed(turn=3))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            conditions.exclusive = ASLEEP
        self.assertEqual(conditions.names(), ("poison", "paralysis"))
        self.assertEqual(SpecialConditions(exclusive=Asleep()).names(), ("sleep",))
        self.assertEqual(Asleep(), ASLEEP)


class ConditionInvariantTest(unittest.TestCase):
    def test_valid_combinations(self):
        for spec in ({"sleep": True}, {"paralysis": 3}, {"poison": 10, "sleep": True}, {"poison": 10, "paralysis": 2}):
            with self.subTest(spec=spec):
                state = build_test_state([{"active": PARAS}, {"active": {"card": GROWLITHE, **spec}}])
                self.assertEqual(check_invariants(state), [])

    def test_bench_pokemon_cannot_be_asleep_or_paralyzed(self):
        for exclusive in (ASLEEP, Paralyzed(turn=3)):
            state = build_test_state([{"active": PARAS, "bench": [PONYTA]}, {"active": GROWLITHE}])
            state.players[0].bench[0].conditions = SpecialConditions(exclusive=exclusive)
            self.assertTrue(any("ベンチ" in p for p in check_invariants(state)))

    def test_wrong_exclusive_values(self):
        for bad in ("sleep", Poison(10), 1):
            with self.subTest(bad=bad):
                state = build_test_state([{"active": PARAS}, {"active": GROWLITHE}])
                state.players[1].active.conditions = SpecialConditions(exclusive=bad)
                self.assertTrue(check_invariants(state))

    def test_paralysis_turn_must_be_valid_and_not_overdue(self):
        """マヒ状態になった番は 1〜今の番。回復する番が過ぎたマヒは残らない（4 番の終わりに回復するものが 5 番に残っていない）。"""
        for turn in (0, 4, "3", None):
            with self.subTest(turn=turn):
                state = build_test_state([{"active": PARAS}, {"active": GROWLITHE}])
                state.players[1].active.conditions = SpecialConditions(exclusive=Paralyzed(turn=turn))
                self.assertTrue(check_invariants(state))
        # プレイヤー 1 が 1 番（相手の番）にマヒ状態 → 2 番の終わりに回復するはず。3 番に残っていたら違反
        state = build_test_state([{"active": PARAS}, {"active": {"card": GROWLITHE, "paralysis": 1}}])
        self.assertTrue(any("回復しているはず" in p for p in check_invariants(state)))
        # 2 番・3 番なら 4 番の終わりに回復する（まだ）
        for turn in (2, 3):
            state = build_test_state([{"active": PARAS}, {"active": {"card": GROWLITHE, "paralysis": turn}}])
            self.assertEqual(check_invariants(state), [])

    def test_poison_rules_still_apply(self):
        state = build_test_state([{"active": PARAS}, {"active": GROWLITHE}])
        state.players[1].active.conditions = SpecialConditions(poison=Poison(15), exclusive=ASLEEP)
        self.assertTrue(check_invariants(state))

    def test_log_turn_field_cannot_be_overwritten(self):
        """ログの turn はいつも今の番（イベントの項目では上書きしない。マヒのイベントは paralyzed_turn を使う）。"""
        state = build_test_state([{"active": PARAS}, {"active": GROWLITHE}])
        with self.assertRaises(ValueError):
            state.add_event("test", turn=1)

    def test_poison_function_keeps_sleep(self):
        state = build_test_state([{"active": PARAS}, {"active": {"card": GROWLITHE, "sleep": True}}])
        poison(state, 1, state.players[1].active, effect="test")
        self.assertEqual(state.players[1].active.conditions, SpecialConditions(poison=NORMAL_POISON, exclusive=ASLEEP))
        self.assertEqual(copy_rng(state.rng).getstate(), state.rng.getstate())


if __name__ == "__main__":
    unittest.main()
