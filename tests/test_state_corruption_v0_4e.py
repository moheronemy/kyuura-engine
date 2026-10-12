"""わざと壊した状態を、不変条件（``check_invariants``）で検出できるか（v0.4e の総合監査 12.7）。

正しい状態（同じ盤面の、壊す前の状態）は拒否しないことも、同じテストで確かめる（不変条件を強めても、合法な状態を
誤って拒否しない）。盤面は ``build_test_state`` で直接作る（1 か所の不変条件を確かめるテスト）か、正式な対戦開始
（``new_game``）から進める。

v0.4e の監査で見つけた検出の漏れ（docs/integration-audit-v0.4e.md 4 章。どれも、壊した状態を ``apply_command`` に渡したときに
だけ問題になる。``new_game`` と ``apply_command`` から作った状態では起こらない）:

- C1: トレーナーの効果の途中の決定（きずぐすり・ポケモンいれかえ・ディフェンダー。v0.2b・v0.2e）の、決定するプレイヤー・
  選べるもの・選ぶ数・種類を確かめていなかった。相手の場のポケモン・場にいない番号が選べるものに入っていても検出できず、
  そのまま答えると相手のポケモンのダメージカウンターをとりのぞけた（p.254「あなたの場にいるポケモン」）
- C2: サイドを取る・バトル場に出す決定（v0.1 からある種類）の再開先（``resume``）と種類の対応、選ぶ数（1 つ）を、ポケモン
  チェックの中の決定のときにしか確かめていなかった（p.312・p.313・p.323）
- C3: サイドを取るプレイヤーの並び（決定するプレイヤーと残り）が、直前のきぜつ（ログ ``knock_out``）から決まる「だれが何枚
  取るか」（きぜつしたポケモンの相手側のプレイヤー。p.323・p.324。残りのサイドより多くは取らない）と同じかを確かめていなかった。
  同時のきぜつで両方が取る順番は番のプレイヤーが選べる（p.325。エンジンは正規化している）ので、順番は確かめない
- C4: 両方のプレイヤーがバトル場に出すときの順番（番でないプレイヤーが先。pp.323〜324）を確かめていなかった
- C5: 番の番号を偶数だけずらした状態（番のプレイヤーは合ったまま）を検出できなかった。最後の番の始まり（ログ ``turn_start``）の
  番・プレイヤーと、状態の番・番のプレイヤーが同じかを確かめる
"""

import dataclasses
import unittest

from kyuura_engine import (
    EndTurn, PlayTrainer, PromoteActive, ResolveDecision, TakePrize, UseAttack, apply_command, check_invariants, new_game,
)
from kyuura_engine.conditions import NORMAL_POISON
from kyuura_engine.decisions import PROMOTE_ACTIVE, SELECT_POKEMON, TAKE_PRIZE
from kyuura_engine.state import Phase, PreventDamage, SpecialConditions

from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, FIRE, FIRE_DECK, GRASS, GROWLITHE, LIGHTNING, METAPOD, PIKACHU, PONYTA, POTION, RATTATA, SWITCH,
    T, WATER_FIGHTING_DECK, build_test_state, finish_setup, uids, with_coin_results,
)


class CorruptionTestCase(unittest.TestCase):
    def assert_detects(self, state, fragment):
        problems = check_invariants(state)
        self.assertTrue(any(fragment in p for p in problems), (fragment, problems))

    def assert_legal(self, state):
        self.assertEqual(check_invariants(state), [])


def trainer_decision(card_id):
    """自分の番に、トレーナー ``card_id`` の効果の決定を待っている状態（相手の場にもポケモンが 2 匹いる）。"""
    state = build_test_state([
        {"active": {"card": GROWLITHE, "damage": 20}, "bench": [RATTATA], "hand": [POTION, SWITCH, DEFENDER]},
        {"active": RATTATA, "bench": [PONYTA]},
    ])
    return apply_command(state, PlayTrainer(0, uids(state, 0, "hand", card_id)[0]))


class TrainerDecisionCorruptionTest(CorruptionTestCase):
    """C1: トレーナーの効果の途中の決定（p.254「あなたの場にいるポケモン」「あなたの控えポケモン」・p.257「あなたの場にいる
    ポケモン」・p.310 トレーナーを使ったプレイヤーがその説明にしたがう）。"""

    CARDS = (POTION, SWITCH, DEFENDER)

    def test_legal_trainer_decisions_pass(self):
        for card_id in self.CARDS:
            with self.subTest(card=card_id):
                state = trainer_decision(card_id)
                self.assertEqual((state.phase, state.decision.kind, state.decision.player), (Phase.DECISION, SELECT_POKEMON, 0))
                self.assert_legal(state)

    def test_wrong_player_is_detected(self):
        for card_id in self.CARDS:
            with self.subTest(card=card_id):
                state = trainer_decision(card_id)
                state.decision = dataclasses.replace(state.decision, player=1)
                self.assert_detects(state, "決定するのが")

    def test_options_with_the_opponents_pokemon_are_detected(self):
        for card_id in self.CARDS:
            with self.subTest(card=card_id):
                state = trainer_decision(card_id)
                opponent = state.players[1].active.pokemon_id
                state.decision = dataclasses.replace(state.decision, options=(*state.decision.options, opponent))
                self.assert_detects(state, "選べるもの")

    def test_options_with_a_pokemon_not_in_play_are_detected(self):
        """場にいない番号（きぜつして場を離れたポケモンの番号など。番号は使い回さない）が選べるものに入っている。"""
        for card_id in self.CARDS:
            with self.subTest(card=card_id):
                state = trainer_decision(card_id)
                state.decision = dataclasses.replace(state.decision, options=(*state.decision.options, 999))
                self.assert_detects(state, "選べるもの")

    def test_missing_options_and_wrong_counts_and_kinds_are_detected(self):
        for card_id in self.CARDS:
            with self.subTest(card=card_id):
                base = trainer_decision(card_id)
                d = base.decision
                for change, fragment in (
                    (dict(options=d.options[:-1] or (999,)), "選べるもの"),
                    (dict(max_choices=2), "選ぶ数"),
                    (dict(kind="forced_switch"), "種類"),
                ):
                    state = base.clone()
                    state.decision = dataclasses.replace(d, **change)
                    self.assert_detects(state, fragment)

    def test_potion_unresolved_choices_must_be_the_undamaged_pokemon(self):
        """きずぐすりの「原典で決められない選択」は、ダメージカウンターののっていない自分のポケモン（v0.2b）。"""
        state = trainer_decision(POTION)
        d = state.decision
        self.assertEqual(d.context_value("unresolved_choices"), (state.players[0].bench[0].pokemon_id,))
        broken = state.clone()
        broken.decision = dataclasses.replace(d, context=tuple((k, () if k == "unresolved_choices" else v) for k, v in d.context))
        self.assert_detects(broken, "扱いを決められない")

    def test_corrupted_potion_decision_is_not_answered_silently(self):
        """壊した状態（選べるものに相手のポケモン）は、答える前の検査で見つかる。正しい状態の答えは今までどおり。"""
        state = trainer_decision(POTION)
        opponent = state.players[1].active.pokemon_id
        healed = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        self.assertEqual(healed.players[0].active.damage, 0)
        broken = state.clone()
        broken.decision = dataclasses.replace(state.decision, options=(*state.decision.options, opponent))
        self.assertTrue(check_invariants(broken))


def knocked_out_state():
    """ガーディの「ほのお」で相手のコラッタ（HP 30・ダメージ 20）がきぜつし、サイドを取る決定を待つ（p.323）。"""
    state = build_test_state([
        {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}, "bench": [RATTATA]},
        {"active": {"card": RATTATA, "damage": 20}, "bench": [PONYTA, RATTATA]},
    ])
    return apply_command(state, UseAttack(0, 0))


def double_knock_out_state():
    """ピカチュウの「でんげき」（30、「うら」なら自分にも 10）で、相手のコラッタ（HP 30）と自分のピカチュウ（HP 40・ダメージ 30）が
    同時にきぜつする（p.324。サイドは相手のきぜつのぶんが先。v0.2f。docs/simultaneous-ko-v0.2f.md）。"""
    state = build_test_state([
        {"active": {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING], "damage": 30}, "bench": [RATTATA]},
        {"active": RATTATA, "bench": [PONYTA]},
    ])
    return apply_command(with_coin_results(state, T), UseAttack(0, 1))


class PrizeAndPromotionDecisionCorruptionTest(CorruptionTestCase):
    """C2・C3・C4: サイドを取る（p.312・p.323）・バトル場に出す（p.313・pp.323〜324）決定。"""

    def test_legal_prize_and_promotion_decisions_pass(self):
        state = knocked_out_state()
        self.assertEqual((state.decision.kind, state.decision.player), (TAKE_PRIZE, 0))
        self.assert_legal(state)
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual((state.decision.kind, state.decision.player), (PROMOTE_ACTIVE, 1))
        self.assert_legal(state)
        double = double_knock_out_state()
        self.assertEqual((double.decision.player, double.decision.context_value("remaining")), (0, (1,)))
        self.assert_legal(double)
        double = apply_command(double, TakePrize(0, 0))
        self.assertEqual((double.decision.player, double.decision.context_value("remaining")), (1, ()))
        self.assert_legal(double)
        double = apply_command(double, TakePrize(1, 0))
        # 両方がバトル場に出す: 番でないプレイヤー（1）が先（pp.323〜324）
        self.assertEqual((double.decision.kind, double.decision.player, double.decision.context_value("remaining")), (PROMOTE_ACTIVE, 1, (0,)))
        self.assert_legal(double)

    def test_resume_must_match_the_kind(self):
        """C2: v0.1 からある種類の決定の再開先は、その種類のもの（ワザのあとの決定でも、ポケモンチェックの中の決定でも）。"""
        prize = knocked_out_state()
        promote = apply_command(prize, TakePrize(0, 0))
        for state, resume in ((prize, "promote_active"), (promote, "take_prize")):
            broken = state.clone()
            broken.decision = dataclasses.replace(state.decision, resume=resume)
            self.assert_detects(broken, "再開先")

    def test_prize_and_promotion_choose_exactly_one(self):
        prize = knocked_out_state()
        promote = apply_command(prize, TakePrize(0, 0))
        for state in (prize, promote):
            broken = state.clone()
            broken.decision = dataclasses.replace(state.decision, max_choices=2)
            self.assert_detects(broken, "選ぶ数")

    def test_prize_taker_must_be_the_opponent_of_the_knocked_out_pokemon(self):
        """C3: きぜつしたのはプレイヤー 1 のポケモンなので、サイドを取るのはプレイヤー 0（p.323）。"""
        state = knocked_out_state()
        broken = state.clone()
        broken.decision = dataclasses.replace(state.decision, player=1)
        self.assert_detects(broken, "サイドを取るプレイヤーの並び")
        extra = state.clone()
        extra.decision = dataclasses.replace(state.decision, context=(("remaining", (0,)),))
        self.assert_detects(extra, "サイドを取るプレイヤーの並び")

    def test_simultaneous_prize_queue_must_follow_the_knock_outs(self):
        """C3: 同時のきぜつ（p.324）で、両方が 1 枚ずつ取る。エンジンは「相手のきぜつのぶん（0）→ 自分のきぜつのぶん（1）」に
        正規化している（v0.2f）が、順番は番のプレイヤーが選べる（p.325）ので、入れ替えた並びは拒否しない（tests/test_simultaneous_ko.py
        の PrizeOrderTest がその並びで最後まで進める）。取る人・枚数が違えば検出する。"""
        state = double_knock_out_state()
        swapped = state.clone()
        swapped.decision = dataclasses.replace(state.decision, player=1, context=(("remaining", (0,)),))
        self.assert_legal(swapped)
        dropped = state.clone()
        dropped.decision = dataclasses.replace(state.decision, context=(("remaining", ()),))
        self.assert_detects(dropped, "サイドを取るプレイヤーの並び")
        after_first = apply_command(state, TakePrize(0, 0))
        again = after_first.clone()
        again.decision = dataclasses.replace(after_first.decision, player=0)
        self.assert_detects(again, "サイドを取るプレイヤーの並び")

    def test_promotion_order_puts_the_non_turn_player_first(self):
        """C4: 両方がバトル場に出すときは、今が番でないプレイヤーが先に出す（pp.323〜324）。"""
        state = double_knock_out_state()
        state = apply_command(apply_command(state, TakePrize(0, 0)), TakePrize(1, 0))
        d = state.decision
        broken = state.clone()
        broken.decision = dataclasses.replace(d, player=0, options=tuple(p.pokemon_id for p in state.players[0].bench),
                                              context=(("remaining", (1,)),))
        self.assert_detects(broken, "バトル場に出す順番")
        # 正しい順番なら最後まで進む
        state = apply_command(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assert_legal(state)
        state = apply_command(state, PromoteActive(0, state.players[0].bench[0].card))
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))

    def test_a_knocked_out_pokemon_cannot_remain_an_option(self):
        state = apply_command(knocked_out_state(), TakePrize(0, 0))
        gone = [pid for pid in range(1, state.next_pokemon_id) if state.find_pokemon(pid) is None]
        self.assertEqual(gone, [3])  # 相手のコラッタ（場のポケモンの番号 3）はきぜつして場を離れた
        broken = state.clone()
        broken.decision = dataclasses.replace(state.decision, options=(*state.decision.options, gone[0]))
        self.assert_detects(broken, "選べるもの")


class TurnNumberCorruptionTest(CorruptionTestCase):
    """C5: 番は先攻から 1 つずつ交互に進む（p.309）。状態の番と番のプレイヤーは、最後の番の始まり（ログ turn_start）と同じ。"""

    def played(self):
        state = finish_setup(new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1))
        return apply_command(apply_command(state, EndTurn(0)), EndTurn(1))

    def test_legal_turn_passes(self):
        state = self.played()
        self.assertEqual((state.turn_number, state.current_player), (3, 0))
        self.assert_legal(state)

    def test_turn_number_shifted_by_two_is_detected(self):
        state = self.played()
        for shift in (2, -2, 10):
            broken = state.clone()
            broken.turn_number += shift
            self.assert_detects(broken, "番の始まり")

    def test_turn_start_of_the_other_player_is_detected(self):
        state = self.played()
        broken = state.clone()
        log = list(broken.log)
        start = max(i for i, e in enumerate(log) if e["kind"] == "turn_start")
        log[start] = {**log[start], "player": 1}
        broken.log = tuple(log)
        self.assert_detects(broken, "番の始まり")


class EarlierCorruptionCatalogueTest(CorruptionTestCase):
    """12.7 のほかの壊し方（v0.4d までの不変条件で検出できるもの）を、進化・持続する効果・ワザの途中の決定のある盤面でまとめて
    確かめる（検出できることの回帰テスト）。"""

    def board(self):
        # バタフリー（2 進化。下にキャタピー・トランセル）が「ふきとばし」を使い、相手が控えを選ぶ決定を待つ（p.19・p.213）
        state = build_test_state([
            {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, "bench": [RATTATA]},
            {"active": {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 4}, "bench": [PONYTA, RATTATA]},
        ], turn_number=5)
        return apply_command(state, UseAttack(0, 0))

    def test_board_is_legal(self):
        state = self.board()
        self.assertEqual((state.decision.kind, state.decision.player), ("forced_switch", 1))
        self.assert_legal(state)

    def test_catalogue(self):
        base = self.board()
        attacker = lambda s: s.players[0].active  # noqa: E731
        defender = lambda s: s.players[1].active  # noqa: E731

        def duplicate_uid(s):
            s.players[0].hand.append(s.players[0].discard[0] if s.players[0].discard else attacker(s).energy[0])

        def lose_stack_card(s):
            attacker(s).evolution_stack = attacker(s).evolution_stack[1:]

        def duplicate_pokemon_id(s):
            s.players[1].bench[0].pokemon_id = attacker(s).pokemon_id

        def wrong_stage(s):
            attacker(s).evolution_stack = tuple(reversed(attacker(s).evolution_stack))

        def bench_condition(s):
            s.players[1].bench[0].conditions = SpecialConditions(poison=NORMAL_POISON)

        def expired_effect(s):
            effect = defender(s).persistent_effects[0]
            defender(s).persistent_effects = (dataclasses.replace(effect, created_turn=2, active_turn=3),)

        def effect_on_the_wrong_pokemon(s):
            defender(s).persistent_effects = (PreventDamage(attacker(s).card, 0, 4, 5),)

        def decision_player(s):
            s.decision = dataclasses.replace(s.decision, player=0)

        def knocked_out_target(s):
            s.decision = dataclasses.replace(s.decision, context=(s.decision.context[0], ("target", s.next_pokemon_id + 3)))

        def turn_owner(s):
            s.current_player = 1

        for mutate, fragment in (
            (duplicate_uid, "2 か所"),
            (lose_stack_card, "どこにもない"),
            (duplicate_pokemon_id, "番号が重なっている"),
            (wrong_stage, "重なり"),
            (bench_condition, "ベンチのポケモン"),
            (expired_effect, "持続する効果"),
            (effect_on_the_wrong_pokemon, "発生源"),
            (decision_player, "ふきとばし"),
            (knocked_out_target, "ふきとばし"),
            (turn_owner, "番のプレイヤー"),
        ):
            with self.subTest(mutate=mutate.__name__):
                state = base.clone()
                mutate(state)
                self.assert_detects(state, fragment)


if __name__ == "__main__":
    unittest.main()
