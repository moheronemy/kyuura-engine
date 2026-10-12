"""プラスパワー（PMCG1-081、v0.2c）: つけて使うトレーナー・ダメージ計算の 5 段階・番の終わりのトラッシュ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES・ERR-PLUSPOWER）:

- p.257 最新の説明: 「このカードはあなたの対戦ポケモンにつけて使い、あなたの番の終わりにトラッシュする。
  このカードをつけているポケモンのワザが、対戦ポケモンにダメージを与えるとき、そのダメージは「+10」
  される。(控えポケモンへのダメージは、そのまま)」
- p.321 ダメージ計算の順番: 1 基本 → 2 ワザを使うポケモンの効果（ここまでで 0 以下なら終わり）→ 3 弱点 →
  4 抵抗力 → 5 ワザを使うポケモンについているトレーナーカードなどの効果（プラスパワー）→ 6〜8。
  計算の途中で 0 やマイナスになってもかまわない。最後に 0 以下なら「ダメージを与えなかった」
- p.313: ポケモンにつけて使うトレーナーカードは、それをつけているポケモンのいる場所にある
- p.311: にげるとき、ついているカード（ポケモンにつけて使うトレーナーカードを含む）はいっしょに移動する
- p.323: きぜつしたら、そのポケモンと、ついていたすべてのカードをトラッシュする
- p.310: トレーナーは 1 番に何枚でも使える

盤面を直接作る build_test_state は 1 か所の規定を確かめるテストに使う。正式な対戦開始からのテストは
test_pluspower_games.py。トレーナーを使う対戦の状態は、形式 4 の state_to_dict で比べる。
"""

import copy
import dataclasses
import json
import pickle
import unittest

from kyuura_engine import (
    EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack,
    apply_command, check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract
from kyuura_engine.damage import DamageModifier, calculate_attack_damage
from kyuura_engine.effects import DEFAULT_EFFECTS, AttachedAttackBonus, TrainerEffect, TrainerEntry
from kyuura_engine.rules import RULES_2000_02_14
from kyuura_engine.state import AttachedTrainer
from kyuura_engine.zones import attach_trainer

from tests.helpers import (
    BILL, DIGLETT, FIGHTING, FIRE, GROWLITHE, LIGHTNING, MACHOP, PLUSPOWER, PONYTA, POTION, RATTATA, SEEL, STARYU,
    SUPER_POTION, SWITCH, VOLTORB, WATER, active, build_test_state,
)


def full(state):
    """ついているトレーナーも表せる状態の辞書（形式 4）。"""
    return state_to_dict(state, format_version=4)


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def kinds(state, *names):
    return [e["kind"] for e in state.log if e["kind"] in names]


def play_pluspowers(state, player=0, count=None):
    cards = hand(state, player, PLUSPOWER)
    for card in cards[:count]:
        state = apply_command(state, PlayTrainer(player, card))
    return state


class RejectsMixin:
    def assert_rejected(self, state, command, code, error=IllegalActionError):
        before = full(state)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual(full(state), before)  # 拒否しても状態は変わらない
        return ctx.exception


# ---------------------------------------------------------------- 登録と使用（11.1）


class PlusPowerRegistryTest(unittest.TestCase):
    def test_registered_by_card_id_with_the_latest_description(self):
        entry = DEFAULT_EFFECTS.trainer_entry(PLUSPOWER)
        definition = load_card_pool().get(PLUSPOWER)
        self.assertIsInstance(entry.effect, AttachedAttackBonus)
        self.assertEqual(entry.effect.amount, 10)
        self.assertTrue(entry.effect.stays_in_play)
        self.assertEqual((entry.name_ja, entry.text_ja), (definition.name_ja, definition.trainer_text_ja))
        self.assertIn("(控えポケモンへのダメージは、そのまま)", entry.play_text_ja)
        self.assertEqual(entry.source, "P43 p.257")
        self.assertTrue(definition.supported)
        self.assertTrue(load_card_pool().is_playable(PLUSPOWER))


class PlayPlusPowerTest(RejectsMixin, unittest.TestCase):
    """プラスパワーを使う（p.310・p.257）。PlayTrainer をそのまま使う。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": {"card": STARYU, "energy": [WATER]}, "bench": [PONYTA], "hand": [PLUSPOWER, PLUSPOWER, POTION, FIRE]},
            {"active": GROWLITHE, "hand": [PLUSPOWER]},
        ])
        self.first, self.second = hand(self.state, 0, PLUSPOWER)
        self.potion = hand(self.state, 0, POTION)[0]
        self.theirs = hand(self.state, 1, PLUSPOWER)[0]

    def test_attaches_to_own_active_and_stays_in_play(self):
        new = apply_command(self.state, PlayTrainer(0, self.first))
        holder = active(new, 0)
        self.assertEqual(holder.trainers, [AttachedTrainer(self.first, 0, new.turn_number)])
        self.assertNotIn(self.first, new.players[0].hand)
        self.assertNotIn(self.first, new.players[0].discard)  # 使いすてではない（つけて使う）
        self.assertIsNone(new.trainer_in_use)
        self.assertEqual(new.phase, Phase.MAIN)
        self.assertIsNone(new.decision)  # 対象は自分の対戦ポケモンだけなので、選ぶ決定は出さない
        self.assertEqual(kinds(new, "play_trainer", "attach_trainer", "discard_trainer"), ["play_trainer", "attach_trainer"])
        event = new.log[-1]
        self.assertEqual((event["pokemon"], event["pokemon_id"]), (holder.card, holder.pokemon_id))
        self.assertEqual(check_invariants(new), [])

    def test_bench_is_not_a_target(self):
        """つけるのは「あなたの対戦ポケモン」だけ（p.257）。ベンチのポケモンにはつかない。"""
        new = apply_command(self.state, PlayTrainer(0, self.first))
        self.assertEqual(new.players[0].bench[0].trainers, [])

    def test_not_your_turn_and_other_players_card(self):
        self.assert_rejected(self.state, PlayTrainer(1, self.theirs), "NOT_YOUR_TURN")
        self.assert_rejected(self.state, PlayTrainer(0, self.theirs), "CARD_NOT_IN_HAND")

    def test_invalid_uid(self):
        self.assert_rejected(self.state, PlayTrainer(0, 9999), "CARD_NOT_IN_HAND")
        self.assert_rejected(self.state, PlayTrainer(0, False), "BAD_COMMAND")

    def test_same_card_twice(self):
        new = apply_command(self.state, PlayTrainer(0, self.first))
        self.assert_rejected(new, PlayTrainer(0, self.first), "CARD_NOT_IN_HAND")  # もうポケモンについている

    def test_card_not_in_hand(self):
        state = build_test_state([{"active": STARYU, "discard": [PLUSPOWER]}, {"active": GROWLITHE}])
        self.assert_rejected(state, PlayTrainer(0, state.players[0].discard[0]), "CARD_NOT_IN_HAND")

    def test_unregistered(self):
        """プラスパワーの登録がない登録表の対戦では使えない（効果がないものとして使わない）。"""
        effects = DEFAULT_EFFECTS.without_trainers("test-no-pluspower", [PLUSPOWER])
        state = build_test_state([{"active": STARYU, "hand": [PLUSPOWER]}, {"active": GROWLITHE}], effects=effects)
        self.assertFalse(pool_from_extract(read_extract(), effects).get(PLUSPOWER).supported)
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNSUPPORTED_TRAINER", UnsupportedError)

    def test_wrong_phase_and_pending_decision(self):
        setup = self.state.clone()
        setup.phase = Phase.SETUP_FIRST_PLAYER
        self.assert_rejected(setup, PlayTrainer(0, self.first), "WRONG_PHASE")
        damaged = build_test_state([
            {"active": {"card": STARYU, "damage": 20}, "hand": [POTION, PLUSPOWER]}, {"active": GROWLITHE},
        ])
        pending = apply_command(damaged, PlayTrainer(0, hand(damaged, 0, POTION)[0]))
        self.assertEqual(pending.phase, Phase.DECISION)
        self.assert_rejected(pending, PlayTrainer(0, hand(damaged, 0, PLUSPOWER)[0]), "WRONG_PHASE")


# ---------------------------------------------------------------- ダメージ計算（11.3）


class DamageStepTest(unittest.TestCase):
    """プラスパワーはダメージ計算の 5 段階（弱点・抵抗力のあと）に加える（p.321）。最終ダメージに足すのではない。"""

    pool = load_card_pool()

    def calc(self, attacker, defender, base, plus=0):
        modifiers = [DamageModifier(5, 10, "プラスパワー", source=i) for i in range(plus)]
        return calculate_attack_damage(base, self.pool.get(attacker), self.pool.get(defender), RULES_2000_02_14, modifiers)

    def test_without_modifiers_the_calculation_is_unchanged(self):
        """変更効果がなければ、v0.1〜v0.2b と同じ計算と段階の記録（固定ダメージのワザ）。"""
        for attacker, defender, base, steps in (
            (MACHOP, GROWLITHE, 20, [("1 基本となる計算", 20)]),
            (STARYU, GROWLITHE, 20, [("1 基本となる計算", 20), ("3 弱点", 40)]),
            (VOLTORB, DIGLETT, 10, [("1 基本となる計算", 10), ("4 抵抗力", -20)]),
        ):
            calc = self.calc(attacker, defender, base)
            self.assertEqual(list(calc.steps), steps)
            self.assertEqual(calc.modifiers, ())

    def test_plus_ten(self):
        calc = self.calc(MACHOP, GROWLITHE, 20, plus=1)
        self.assertEqual((calc.final, [s[1] for s in calc.steps]), (30, [20, 30]))
        self.assertEqual(calc.steps[-1][0], "5 プラスパワー")

    def test_weakness_is_doubled_before_pluspower(self):
        """ヒトデマン（水）ひらてうち 20 → ガーディ（弱点 水）: 20 × 2 + 10 = 50（(20 + 10) × 2 = 60 ではない）。"""
        calc = self.calc(STARYU, GROWLITHE, 20, plus=1)
        self.assertEqual((calc.final, [s[1] for s in calc.steps]), (50, [20, 40, 50]))

    def test_resistance_then_pluspower_keeps_the_negative_value(self):
        """ビリリダマ（雷）たいあたり 10 → ディグダ（抵抗力 雷 -30）: 10 − 30 + 10 = −10 → 0（ダメージを与えなかった）。

        途中の 0・マイナスはそのまま続ける（p.321）。抵抗力のあとで 0 にしてから +10 すると 10 になってしまう。
        """
        calc = self.calc(VOLTORB, DIGLETT, 10, plus=1)
        self.assertEqual((calc.final, [s[1] for s in calc.steps]), (0, [10, -20, -10]))

    def test_several_pluspowers_add_up_at_step_5(self):
        """複数枚は 5 段階でそれぞれ +10（加算なので順番で結果は変わらない）。10 − 30 + 30 = 10。"""
        calc = self.calc(VOLTORB, DIGLETT, 10, plus=3)
        self.assertEqual((calc.final, [s[1] for s in calc.steps]), (10, [10, -20, -10, 0, 10]))
        calc = self.calc(MACHOP, GROWLITHE, 20, plus=2)
        self.assertEqual(calc.final, 40)

    def test_no_damage_attack_stops_before_pluspower(self):
        """2 段階までで 0 以下なら計算を終える。ダメージを与えないワザにプラスパワーは効かない（p.321、p.257 の解説）。"""
        calc = self.calc(MACHOP, GROWLITHE, 0, plus=1)
        self.assertEqual((calc.final, calc.stopped_after_step_2), (0, True))

    def test_only_steps_2_and_5_to_8_take_modifiers(self):
        with self.assertRaises(ValueError):
            DamageModifier(3, 10, "x")


class PlusPowerAttackTest(unittest.TestCase):
    """対戦の中で、ワザのダメージに 5 段階で加わる。"""

    def attack(self, attacker, defender, *, plus, defender_bench=(), prizes=6, energy=None):
        state = build_test_state([
            {"active": {"card": attacker, "energy": energy or [FIGHTING]}, "hand": [PLUSPOWER] * plus, "prizes": prizes},
            {"active": defender, "bench": list(defender_bench)},
        ])
        state = play_pluspowers(state)
        return apply_command(state, UseAttack(0, 0))

    def damage_event(self, state):
        return [e for e in state.log if e["kind"] == "damage"][-1]

    def test_damage_without_pluspower(self):
        state = self.attack(MACHOP, DIGLETT, plus=0, defender_bench=[RATTATA])
        self.assertEqual(active(state, 1).damage, 20)
        self.assertNotIn("modifiers", self.damage_event(state))  # 変更効果がなければ v0.1 と同じ形

    def test_exactly_hp_knocks_out(self):
        """ワンリキー けたぐり 20 + 10 = 30 = ディグダの HP 30 → きぜつ（HP 以上。p.323）。"""
        state = self.attack(MACHOP, DIGLETT, plus=1, defender_bench=[RATTATA])
        event = self.damage_event(state)
        self.assertEqual((event["amount"], event["modifiers"]), (30, ((5, hand_card(state, PLUSPOWER), 10),)))
        self.assertIn("knock_out", kinds(state, "knock_out"))
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)

    def test_more_than_hp_knocks_out(self):
        state = self.attack(MACHOP, DIGLETT, plus=2, defender_bench=[RATTATA])
        self.assertEqual(self.damage_event(state)["amount"], 40)
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)

    def test_resistance_with_pluspower_in_a_game(self):
        """ビリリダマ（雷）たいあたり 10 → ディグダ（抵抗力 雷 -30）。1 枚: −20 + 10 → 0。3 枚: −20 + 30 → 10（p.321）。"""
        one = self.attack(VOLTORB, DIGLETT, plus=1, defender_bench=[RATTATA], energy=[LIGHTNING])
        self.assertEqual((active(one, 1).damage, self.damage_event(one)["amount"]), (0, 0))
        three = self.attack(VOLTORB, DIGLETT, plus=3, defender_bench=[RATTATA], energy=[LIGHTNING])
        self.assertEqual((active(three, 1).damage, self.damage_event(three)["steps"][-1]), (10, ("5 プラスパワー", 10)))

    def test_one_pluspower_is_applied_once(self):
        state = self.attack(MACHOP, GROWLITHE, plus=1, defender_bench=[RATTATA])
        self.assertEqual(active(state, 1).damage, 30)
        self.assertEqual(len(self.damage_event(state)["modifiers"]), 1)

    def test_last_prize_wins_and_the_game_ends_without_a_turn_end(self):
        """最後のサイドを取って勝ち（p.311）。対戦が終わるので番の終わりは来ず、プラスパワーはついたまま。"""
        state = self.attack(MACHOP, DIGLETT, plus=1, defender_bench=[RATTATA], prizes=1)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (0,)))
        self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 0))
        self.assertEqual(len(active(state, 0).trainers), 1)
        self.assertEqual(state.log[-1]["kind"], "game_end")  # 勝敗のあとに効果の処理はない
        self.assertEqual(kinds(state, "discard_attached_trainer"), [])
        self.assertEqual(check_invariants(state), [])
        json.dumps(full(state))

    def test_no_bench_after_knock_out_wins(self):
        state = self.attack(STARYU, GROWLITHE, plus=2, energy=[WATER])  # 20 × 2 + 20 = 60 = HP
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)  # サイドを取ってから勝ち負けを判定する（p.323）
        state = apply_command(state, ResolveDecision(0, state.decision.id, (0,)))
        self.assertEqual((state.phase, state.result.conditions), (Phase.GAME_OVER, ((0, "OPPONENT_CANNOT_FIELD_ACTIVE"),)))
        self.assertEqual(len(active(state, 0).trainers), 2)


def hand_card(state, card_id):
    """（ワザのあと）ついているプラスパワーのカード uid。"""
    for p in state.players:
        for pokemon in p.in_play():
            for t in pokemon.trainers:
                if state.cards[t.card].card_id == card_id:
                    return t.card
    raise AssertionError("ついていない")


# ---------------------------------------------------------------- 番の終わり（11.4）と持続（11.2）


class TurnEndTest(unittest.TestCase):
    """あなたの番の終わりにトラッシュする（p.257）。番の終わりはポケモンチェックの前（p.309、p.323）。"""

    def state(self, *, bench=(PONYTA,), plus=1, their_bench=(RATTATA,), deck=None):
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": list(bench), "hand": [PLUSPOWER] * plus,
             **({"deck": deck} if deck is not None else {})},
            {"active": GROWLITHE, "bench": list(their_bench)},
        ])
        return play_pluspowers(state)

    def assert_discarded_once(self, state, cards):
        events = [e for e in state.log if e["kind"] == "discard_attached_trainer"]
        self.assertEqual(sorted(e["card"] for e in events), sorted(cards))
        for card in cards:
            self.assertEqual(state.players[0].discard.count(card), 1)
            self.assertFalse(any(t.card == card for p in state.players for pk in p.in_play() for t in pk.trainers))

    def test_attack_then_turn_end(self):
        state = self.state()
        card = active(state, 0).trainers[0].card
        new = apply_command(state, UseAttack(0, 0))
        self.assert_discarded_once(new, [card])
        order = [e["kind"] for e in new.log[-7:]]
        self.assertEqual(order, ["attack", "damage", "discard_attached_trainer", "turn_end", "pokemon_check", "turn_start", "draw"])
        self.assertEqual(new.current_player, 1)

    def test_end_turn_without_attack(self):
        state = self.state(plus=2)
        cards = [t.card for t in active(state, 0).trainers]
        new = apply_command(state, EndTurn(0))
        self.assert_discarded_once(new, cards)
        # 次の番（相手の番、その次の自分の番）に効果は残らない
        new = apply_command(new, EndTurn(1))
        attacked = apply_command(new, UseAttack(0, 0))
        self.assertNotIn("modifiers", [e for e in attacked.log if e["kind"] == "damage"][-1])
        self.assert_discarded_once(attacked, cards)  # 2 回はトラッシュしない

    def test_retreat_moves_the_card_and_it_is_discarded_from_the_bench(self):
        """にげると、ついているトレーナーカードはポケモンといっしょにベンチへ移る（p.311）。番の終わりにトラッシュ。"""
        state = self.state(bench=(RATTATA,))
        holder = active(state, 0)
        card = holder.trainers[0].card
        state = apply_command(state, Retreat(0, (holder.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].bench[0].pokemon_id, holder.pokemon_id)
        self.assertEqual([t.card for t in state.players[0].bench[0].trainers], [card])
        self.assertEqual(active(state, 0).trainers, [])
        new = apply_command(state, EndTurn(0))
        self.assert_discarded_once(new, [card])
        event = [e for e in new.log if e["kind"] == "discard_attached_trainer"][-1]
        self.assertEqual(event["pokemon_id"], holder.pokemon_id)

    def test_switch_moves_the_card_and_it_is_discarded_at_turn_end(self):
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "bench": [PONYTA], "hand": [PLUSPOWER, SWITCH]},
            {"active": GROWLITHE},
        ])
        state = play_pluspowers(state)
        card = active(state, 0).trainers[0].card
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual([t.card for t in state.players[0].bench[0].trainers], [card])
        new = apply_command(state, EndTurn(0))
        self.assert_discarded_once(new, [card])

    def test_knock_out_by_attack_then_turn_end(self):
        """ワザできぜつさせ、サイドを取り、相手が交代したあとで番が終わる。そのときにトラッシュする。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [PLUSPOWER]},
            {"active": DIGLETT, "bench": [RATTATA]},
        ])
        state = play_pluspowers(state)
        card = active(state, 0).trainers[0].card
        state = apply_command(state, UseAttack(0, 0))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (0,)))
        self.assertEqual(state.phase, Phase.PROMOTE_ACTIVE)
        self.assertEqual(len(active(state, 0).trainers), 1)  # 番はまだ終わっていない
        state = apply_command(state, ResolveDecision(1, state.decision.id, (state.decision.options[0],)))
        self.assert_discarded_once(state, [card])
        order = [e["kind"] for e in state.log if e["kind"] in ("take_prize", "promote_active", "discard_attached_trainer", "turn_end")]
        self.assertEqual(order, ["take_prize", "promote_active", "discard_attached_trainer", "turn_end"])

    def test_deck_out_after_bill(self):
        """マサキで山札がなくなっても負けではない（p.312）。プラスパワーは自分の番の終わりにトラッシュし、
        次の自分の番の最初に引けなくて負け（p.309）。勝敗のあとに効果の処理はない。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [BILL, PLUSPOWER], "deck": [FIRE, FIRE]},
            {"active": GROWLITHE, "deck": [FIRE] * 5},
        ])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
        state = play_pluspowers(state)
        card = active(state, 0).trainers[0].card
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, EndTurn(1))
        self.assertEqual((state.phase, state.result.conditions), (Phase.GAME_OVER, ((1, "OPPONENT_DECK_EMPTY"),)))
        self.assert_discarded_once(state, [card])
        self.assertEqual(state.log[-1]["kind"], "game_end")


class PersistenceTest(unittest.TestCase):
    """ついているトレーナーの状態（11.2）: 有効期限、複製、保存則、きぜつ。"""

    def setUp(self):
        self.state = play_pluspowers(build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [PLUSPOWER]}, {"active": GROWLITHE},
        ]))
        self.attached = active(self.state, 0).trainers[0]

    def test_record_holds_source_owner_target_and_expiry(self):
        self.assertEqual(self.attached, AttachedTrainer(card=self.attached.card, player=0, discard_at_end_of_turn=self.state.turn_number))
        data = full(self.state)["players"][0]["active"]
        self.assertEqual(data["trainers"], [{"card": self.attached.card, "card_id": PLUSPOWER, "player": 0,
                                             "discard_at_end_of_turn": self.state.turn_number}])
        self.assertEqual(data["pokemon_id"], active(self.state, 0).pokemon_id)
        self.assertEqual(full(self.state)["format_version"], 4)

    def test_old_formats_refuse_instead_of_dropping_the_card(self):
        for version in (1, 2, 3):
            with self.assertRaises(ValueError):
                state_to_dict(self.state, format_version=version)

    def test_clone_deepcopy_pickle_keep_and_do_not_share(self):
        command = UseAttack(0, 0)
        expected = full(apply_command(self.state, command))
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertEqual(full(copied), full(self.state))
            self.assertEqual(full(apply_command(copied, command)), expected)
            active(copied, 0).trainers.clear()  # 複製を変えても元は変わらない
            self.assertEqual(len(active(self.state, 0).trainers), 1)

    def test_broken_attachments_are_detected(self):
        card = self.attached.card
        stale = self.state.clone()
        stale.turn_number += 1
        self.assertTrue(any("有効期限" in p for p in check_invariants(stale)))
        doubled = self.state.clone()
        doubled.players[0].discard.append(card)
        self.assertTrue(any("2 か所" in p for p in check_invariants(doubled)))
        lost = self.state.clone()
        active(lost, 0).trainers.clear()
        self.assertTrue(any("どこにもない" in p for p in check_invariants(lost)))
        wrong_kind = self.state.clone()
        potion_like = dataclasses.replace(self.attached, card=wrong_kind.players[0].active.energy[0])
        active(wrong_kind, 0).energy.clear()
        active(wrong_kind, 0).trainers.append(potion_like)
        self.assertTrue(any("トレーナーカードでない" in p for p in check_invariants(wrong_kind)))
        wrong_owner = self.state.clone()
        active(wrong_owner, 0).trainers[0] = dataclasses.replace(self.attached, player=1)
        self.assertTrue(any("持ち主" in p for p in check_invariants(wrong_owner)))

    def test_trainer_without_stays_in_play_cannot_be_attached(self):
        """場に残る実装（stays_in_play）のないトレーナー（きずぐすりなど）がついている状態は不正。"""
        state = build_test_state([{"active": MACHOP, "hand": [POTION]}, {"active": GROWLITHE}])
        potion = state.players[0].hand.pop()
        active(state, 0).trainers.append(AttachedTrainer(potion, 0, state.turn_number))
        self.assertTrue(any("場に残る実装" in p for p in check_invariants(state)))


class KnockOutWithAttachedTrainerTest(unittest.TestCase):
    """きぜつしたら、ついていたトレーナーカードもいっしょにトラッシュする（p.323）。

    プラスパワーは使った番の終わりにトラッシュするので、ついたまま相手のワザを受けることはない。そこで、
    テスト専用の「次の番の終わりまでつく」トレーナー（製品の登録表には入れない）で、場を離れたときの処理を確かめる。
    """

    class UntilNextTurn(TrainerEffect):
        implementation_id = "test_until_next_turn"
        stays_in_play = True

        def resolve(self, state, use):
            attach_trainer(state, use.player, use.card, state.players[use.player].active, state.turn_number + 1)

    def test_attached_card_goes_to_the_discard_with_the_pokemon(self):
        definition = load_card_pool().get(SUPER_POTION)
        effects = DEFAULT_EFFECTS.with_trainers("test-until-next-turn", {
            SUPER_POTION: TrainerEntry(self.UntilNextTurn(), definition.name_ja, definition.trainer_text_ja, "テスト", "テスト"),
        })
        state = build_test_state([
            {"active": RATTATA, "bench": [PONYTA], "hand": [SUPER_POTION]},
            {"active": {"card": MACHOP, "energy": [FIGHTING]}},
        ], effects=effects)
        card = state.players[0].hand[0]
        state = apply_command(state, PlayTrainer(0, card))
        state = apply_command(state, EndTurn(0))
        self.assertEqual(len(active(state, 0).trainers), 1)  # 番の終わりはまだ（次の番の終わりまで）
        state = apply_command(state, UseAttack(1, 0))  # けたぐり 20 + 弱点 → コラッタ（HP 30）きぜつ
        ko = [e for e in state.log if e["kind"] == "knock_out"][-1]
        self.assertEqual(ko["discarded_trainers"], (card,))
        self.assertEqual(state.players[0].discard.count(card), 1)
        state = apply_command(state, ResolveDecision(1, state.decision.id, (0,)))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual(state.players[0].discard.count(card), 1)  # 番の終わりに 2 回目のトラッシュはしない
        self.assertEqual(kinds(state, "discard_attached_trainer"), [])
        self.assertEqual(check_invariants(state), [])


# ---------------------------------------------------------------- v0.2b のトレーナーとの組み合わせ（11.5）


class CombinationTest(unittest.TestCase):
    def test_bill_and_pluspower(self):
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [BILL, PLUSPOWER], "deck": [FIRE] * 5},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, BILL)[0]))
        state = play_pluspowers(state)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 30)
        self.assertEqual(len(state.players[0].discard), 2)  # マサキ（使いすて）とプラスパワー（番の終わり）

    def test_potion_on_the_pokemon_with_pluspower(self):
        """きずぐすりで回復しても、ついているプラスパワーはそのまま（別のカードの効果）。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING], "damage": 30}, "hand": [PLUSPOWER, POTION]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ])
        state = play_pluspowers(state)
        state = apply_command(state, PlayTrainer(0, hand(state, 0, POTION)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (active(state, 0).pokemon_id,)))
        self.assertEqual((active(state, 0).damage, len(active(state, 0).trainers)), (10, 1))
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 30)

    def test_pluspower_before_switch_stays_with_the_old_active(self):
        """プラスパワーのあとでポケモンいれかえ: カードは元のポケモンといっしょにベンチへ。新しい対戦ポケモンのワザには加わらない。"""
        state = build_test_state([
            {"active": MACHOP, "bench": [{"card": STARYU, "energy": [WATER]}], "hand": [PLUSPOWER, SWITCH]},
            {"active": SEEL, "bench": [RATTATA]},
        ])
        state = play_pluspowers(state)
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        state = apply_command(state, UseAttack(0, 0))  # ひらてうち 20（パウワウに弱点・抵抗力なし）
        self.assertEqual(active(state, 1).damage, 20)

    def test_switch_before_pluspower_adds_to_the_new_active(self):
        state = build_test_state([
            {"active": MACHOP, "bench": [{"card": STARYU, "energy": [WATER]}], "hand": [PLUSPOWER, SWITCH]},
            {"active": SEEL, "bench": [RATTATA]},
        ])
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        state = play_pluspowers(state)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 30)

    def test_card_still_attached_after_coming_back_from_the_bench(self):
        """にげてベンチに戻り、もう一度バトル場に出ても、ついているプラスパワーの効果はある（カードはついたまま。
        p.311・p.313。ベンチに戻ると消えるのはワザなどによる「持続する効果」で、ついているカードの効果とは別。p.321・p.322）。"""
        state = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING, FIGHTING]}, "bench": [RATTATA], "hand": [PLUSPOWER]},
            {"active": GROWLITHE, "bench": [PONYTA]},
        ])
        state = play_pluspowers(state)
        machop = active(state, 0)
        state = apply_command(state, Retreat(0, (machop.energy[0],), state.players[0].bench[0].card))
        state = apply_command(state, Retreat(0, (), state.players[0].bench[0].card))  # コラッタのにげるは 0
        self.assertEqual(active(state, 0).pokemon_id, machop.pokemon_id)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(active(state, 1).damage, 30)

    def test_v0_2b_unresolved_cases_are_unchanged(self):
        """プラスパワーがあっても、v0.2b の未解決の場面はそのまま UnsupportedError。"""
        state = build_test_state([{"active": MACHOP, "hand": [PLUSPOWER, POTION, SWITCH]}, {"active": GROWLITHE}])
        state = play_pluspowers(state)
        for card_id, code in ((POTION, "UNRESOLVED_POTION_WITHOUT_DAMAGE"), (SWITCH, "UNRESOLVED_SWITCH_WITHOUT_BENCH")):
            before = full(state)
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(state, PlayTrainer(0, hand(state, 0, card_id)[0]))
            self.assertEqual(ctx.exception.code, code)
            self.assertEqual(full(state), before)


if __name__ == "__main__":
    unittest.main()
