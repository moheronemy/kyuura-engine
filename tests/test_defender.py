"""ディフェンダー（PMCG1-079、v0.2e）: 自分の場のポケモンを選んでつける・ダメージ計算の 7 段階・次の相手の番の終わりまでの有効期限。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。カードの記録 PMCG1-079）:

- p.257 最新の説明: 「このカードは、あなたの場にいるポケモンにつけて使い、次の相手の番の終わりにトラッシュする。
  このカードをつけているポケモンがワザによるダメージを受けるとき、そのダメージは「-20」される。」
- p.321 ダメージ計算の順番: 7 ワザを受けるポケモンについているカードの効果（「ディフェンダー」など）。複数なら順番は
  ワザを受けるプレイヤーが決める。途中の 0・マイナスはかまわない。最後に 0 以下なら「ダメージを受けなかった」
- p.312・p.313: 「自分の場」は自分のバトル場とベンチ。ポケモンにつけて使うトレーナーは、そのポケモンのいる場所にある
- p.309: 番は交互に進む。p.311: にげるとき、ついているカードもいっしょに移る。p.323: きぜつしたら、ついていた
  カードもトラッシュ。p.310: トレーナーは 1 番に何枚でも使える

盤面を直接作る build_test_state は 1 か所の規定を確かめるテストに使う。正式な対戦開始からのテストは
test_defender_games.py。ついているトレーナーのある状態は、形式 4 の state_to_dict で比べる。
"""

import copy
import dataclasses
import pickle
import unittest

from kyuura_engine import (
    EndTurn, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, TakePrize, UnsupportedError, UseAttack,
    apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.effects import DEFAULT_EFFECTS, AttachedDamageReduction
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import AttachedTrainer, GameResult, Halt

from tests.helpers import (
    DEFENDER, DIGLETT, DODUO, DRATINI, FIGHTING, FIRE, GROWLITHE, H, HITMONCHAN, LIGHTNING, MACHOP, PLUSPOWER, PONYTA,
    RATTATA, SEEL, STARYU, SWITCH, T, VOLTORB, WATER, active, build_test_state, with_coin_results,
)
from tests.test_coin_attacks import RESISTANT, TEST_POOL

ATTACKERS = {
    # 相手（プレイヤー 1）のワザ: (カード, エネルギー, ワザの位置)。コメントは基本のダメージとタイプ
    "voltorb": (VOLTORB, [LIGHTNING], 0),  # たいあたり 10（雷）
    "machop": (MACHOP, [FIGHTING], 0),  # けたぐり 20（闘）
    "staryu": (STARYU, [WATER], 0),  # ひらてうち 20（水）
    "ponyta": (PONYTA, [FIRE, FIRE], 1),  # ほのおのしっぽ 30（炎）
    "hitmonchan": (HITMONCHAN, [FIGHTING, FIGHTING, FIGHTING], 1),  # スペシャルパンチ 40（闘）
}


def full(state):
    return state_to_dict(state, format_version=4)


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def play_defender(state, player=0, target=None, card=None):
    """ディフェンダーを使い、``target``（場のポケモンの番号。省略時は対戦ポケモン）につける。"""
    card = card if card is not None else hand(state, player, DEFENDER)[0]
    state = apply_command(state, PlayTrainer(player, card))
    target = target if target is not None else state.players[player].active.pokemon_id
    return apply_command(state, ResolveDecision(player, state.decision.id, (target,)))


def defended(defender_spec, attacker="machop", *, defenders=1, bench=(), their_hand=(), their_prizes=6, prizes=6, pool=None):
    """プレイヤー 0 が対戦ポケモンにディフェンダーを ``defenders`` 枚つけて番を終え、プレイヤー 1 の番になった盤面。"""
    card, energy, _ = ATTACKERS[attacker]
    state = build_test_state([
        {"active": defender_spec, "bench": list(bench), "hand": [DEFENDER] * defenders, "prizes": prizes},
        {"active": {"card": card, "energy": energy}, "bench": [DIGLETT], "hand": list(their_hand), "prizes": their_prizes},
    ], pool=pool)
    for _ in range(defenders):
        state = play_defender(state)
    return apply_command(state, EndTurn(0))


def attack(state, player=1, index=None):
    if index is None:
        index = ATTACKERS_BY_CARD.get(state.card_def(state.players[player].active.card).id, 0)
    start = len(state.log)
    new = apply_command(state, UseAttack(player, index))
    events = [dict(e) for e in new.log[start:]]
    return new, events, next(e for e in events if e["kind"] == "damage")


ATTACKERS_BY_CARD = {card: index for card, _, index in ATTACKERS.values()}


class RejectsMixin:
    def assert_rejected(self, state, command, code, error=IllegalActionError):
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))  # 状態も乱数も変わらない
        return ctx.exception


# ---------------------------------------------------------------- 登録（13.1）


class DefenderRegistryTest(unittest.TestCase):
    def test_registered_with_the_latest_description_of_p257(self):
        from kyuura_engine.cards import load_card_pool, read_verification

        entry = DEFAULT_EFFECTS.trainer_entry(DEFENDER)
        self.assertIsInstance(entry.effect, AttachedDamageReduction)
        self.assertEqual((entry.effect.amount, entry.effect.discard_turn_offset, entry.effect.stays_in_play), (20, 1, True))
        self.assertEqual(entry.source, "P43 p.257")
        record = read_verification()["cards"][DEFENDER]
        self.assertEqual((record["page"], record["status"]), (257, "不一致あり"))
        self.assertEqual(entry.play_text_ja, record["latest_description_ja"])
        # 照合用の文面は kyuura の写し（第1弾の印刷）。最新の説明とはトラッシュする時点が違う（CONFLICT。最新の説明にしたがう）
        definition = load_card_pool().get(DEFENDER)
        self.assertEqual(entry.text_ja, definition.trainer_text_ja)
        self.assertIn("次の自分の番の最初にはがしてすてる", entry.text_ja)
        self.assertIn("次の相手の番の終わりにトラッシュする", entry.play_text_ja)
        self.assertTrue(load_card_pool().is_playable(DEFENDER))


# ---------------------------------------------------------------- 使う（13.1）


class PlayDefenderTest(RejectsMixin, unittest.TestCase):
    def setUp(self):
        self.state = build_test_state([
            {"active": GROWLITHE, "bench": [PONYTA, RATTATA], "hand": [DEFENDER, DEFENDER], "deck": [DEFENDER, FIRE]},
            {"active": MACHOP, "hand": [DEFENDER]},
        ])
        self.card = hand(self.state, 0, DEFENDER)[0]

    def test_play_asks_for_a_pokemon_on_own_field(self):
        fingerprint = rng_fingerprint(self.state.rng)
        state = apply_command(self.state, PlayTrainer(0, self.card))
        d = state.decision
        own = [pokemon.pokemon_id for pokemon in state.players[0].in_play()]
        self.assertEqual((state.phase, d.kind, d.player, d.options), (Phase.DECISION, "select_pokemon", 0, tuple(own)))
        self.assertEqual(d.context_value("unresolved_choices", ()), ())  # 原典で決められない選択はない
        self.assertEqual((state.trainer_in_use.player, state.trainer_in_use.card), (0, self.card))
        self.assertNotIn(self.card, state.players[0].hand)
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)  # 乱数を使わない
        self.assertEqual(check_invariants(state), [])

    def test_only_active_still_asks(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP}])
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(state.decision.options, (state.players[0].active.pokemon_id,))

    def test_rejections_keep_the_state(self):
        their_card = hand(self.state, 1, DEFENDER)[0]
        in_deck = self.state.players[0].deck[0]
        self.assert_rejected(self.state, PlayTrainer(1, their_card), "NOT_YOUR_TURN")
        self.assert_rejected(self.state, PlayTrainer(2, self.card), "INVALID_PLAYER")
        self.assert_rejected(self.state, PlayTrainer(0, 999), "CARD_NOT_IN_HAND")
        self.assert_rejected(self.state, PlayTrainer(0, their_card), "CARD_NOT_IN_HAND")
        self.assert_rejected(self.state, PlayTrainer(0, in_deck), "CARD_NOT_IN_HAND")

    def test_unregistered(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP}],
                                 effects=DEFAULT_EFFECTS.without_trainers("test-no-defender", [DEFENDER]))
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNSUPPORTED_TRAINER", UnsupportedError)

    def test_pending_decision_blocks_other_actions(self):
        state = apply_command(self.state, PlayTrainer(0, self.card))
        other = hand(state, 0, DEFENDER)[0]
        self.assert_rejected(state, PlayTrainer(0, other), "WRONG_PHASE")
        self.assert_rejected(state, UseAttack(0, 0), "WRONG_PHASE")
        self.assert_rejected(state, EndTurn(0), "WRONG_PHASE")

    def test_used_card_cannot_be_played_again(self):
        state = play_defender(self.state, card=self.card)
        self.assert_rejected(state, PlayTrainer(0, self.card), "CARD_NOT_IN_HAND")

    def test_wrong_phase(self):
        attacker = build_test_state([
            {"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [DEFENDER]}, {"active": RATTATA, "bench": [PONYTA]},
        ])
        state = apply_command(attacker, UseAttack(0, 0))  # けたぐり 20 + 弱点 → コラッタきぜつ → サイドの決定
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "WRONG_PHASE")

    def test_finished_and_halted_games(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP}])
        state.phase = Phase.GAME_OVER
        state.result = GameResult("win", 0, ((0, "ALL_PRIZES_TAKEN"),))
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "GAME_OVER")
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP}])
        state.phase = Phase.HALTED
        state.halt = Halt("UNRESOLVED_MULLIGAN_COMPENSATION", "テスト", ())
        self.assert_rejected(state, PlayTrainer(0, state.players[0].hand[0]), "UNRESOLVED_MULLIGAN_COMPENSATION", UnsupportedError)


# ---------------------------------------------------------------- 対象の選択（13.2）


class ChooseTargetTest(RejectsMixin, unittest.TestCase):
    def setUp(self):
        self.base = build_test_state([
            {"active": GROWLITHE, "bench": [PONYTA, RATTATA, DRATINI], "hand": [DEFENDER]},
            {"active": MACHOP, "bench": [STARYU]},
        ])
        self.card = self.base.players[0].hand[0]
        self.state = apply_command(self.base, PlayTrainer(0, self.card))
        self.d = self.state.decision

    def resolve(self, state, choices, player=0, decision=None):
        return apply_command(state, ResolveDecision(player, decision if decision is not None else state.decision.id, choices))

    def test_active(self):
        target = self.state.players[0].active
        state = self.resolve(self.state, (target.pokemon_id,))
        self.assertEqual(active(state, 0).trainers, [AttachedTrainer(self.card, 0, self.state.turn_number + 1)])
        self.assertIsNone(state.trainer_in_use)
        self.assertEqual(state.phase, Phase.MAIN)
        attach = [dict(e) for e in state.log if e["kind"] == "attach_trainer"][-1]
        self.assertEqual((attach["card"], attach["pokemon_id"], attach["discard_at_end_of_turn"]),
                         (self.card, target.pokemon_id, self.state.turn_number + 1))

    def test_bench_choice_among_several(self):
        target = self.state.players[0].bench[1]  # ベンチの 2 匹目（コラッタ）
        state = self.resolve(self.state, (target.pokemon_id,))
        self.assertEqual([t.card for t in state.players[0].bench[1].trainers], [self.card])
        self.assertEqual([pokemon.trainers for i, pokemon in enumerate(state.players[0].in_play()) if i != 2], [[], [], []])

    def test_invalid_choices_keep_the_card_in_use(self):
        theirs = self.state.players[1].active.pokemon_id
        their_bench = self.state.players[1].bench[0].pokemon_id
        own = self.state.players[0].active.pokemon_id
        for choices, code in (((theirs,), "INVALID_CHOICE"), ((their_bench,), "INVALID_CHOICE"), ((999,), "INVALID_CHOICE"),
                              ((), "INVALID_CHOICE_COUNT"), ((own, self.d.options[1]), "INVALID_CHOICE_COUNT"),
                              ((self.state.players[0].active.card,), "INVALID_CHOICE")):
            with self.subTest(choices=choices):
                self.assert_rejected(self.state, ResolveDecision(0, self.d.id, choices), code)
        self.assertEqual(self.state.trainer_in_use.card, self.card)

    def test_wrong_decision_id_and_player(self):
        own = self.state.players[0].active.pokemon_id
        self.assert_rejected(self.state, ResolveDecision(0, self.d.id - 1, (own,)), "WRONG_DECISION")
        self.assert_rejected(self.state, ResolveDecision(0, self.d.id + 1, (own,)), "WRONG_DECISION")
        self.assert_rejected(self.state, ResolveDecision(1, self.d.id, (own,)), "NOT_YOUR_DECISION")

    def test_second_answer_is_rejected(self):
        own = self.state.players[0].active.pokemon_id
        state = self.resolve(self.state, (own,))
        self.assert_rejected(state, ResolveDecision(0, self.d.id, (own,)), "WRONG_PHASE")
        self.assertEqual(len(active(state, 0).trainers), 1)  # 二重につかない

    def test_copies_of_the_pending_state_resolve_the_same(self):
        own = self.state.players[0].bench[0].pokemon_id
        expected = full(self.resolve(self.state, (own,)))
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertEqual(full(self.resolve(copied, (own,))), expected)
        self.assertEqual(self.state.trainer_in_use.card, self.card)  # 元の状態は決定を待ったまま

    def test_card_is_in_exactly_one_place(self):
        places = lambda s: (self.card in s.players[0].hand, s.trainer_in_use is not None and s.trainer_in_use.card == self.card,
                            any(t.card == self.card for p in s.players[0].in_play() for t in p.trainers), self.card in s.players[0].discard)
        self.assertEqual(places(self.base), (True, False, False, False))
        self.assertEqual(places(self.state), (False, True, False, False))
        self.assertEqual(places(self.resolve(self.state, (self.d.options[0],))), (False, False, True, False))


# ---------------------------------------------------------------- 防御の効果（13.3）


class DefenderDamageTest(unittest.TestCase):
    """相手の番に、相手のワザで受けるダメージを 7 段階で -20（p.257・p.321）。"""

    def test_base_damage_10_20_30_40(self):
        for attacker, base, amount in (("voltorb", 10, 0), ("machop", 20, 0), ("ponyta", 30, 10), ("hitmonchan", 40, 20)):
            with self.subTest(attacker=attacker):
                state = defended(GROWLITHE, attacker)
                defender_card = active(state, 0).trainers[0].card
                _, _, damage = attack(state)
                self.assertEqual(damage["steps"], (("1 基本となる計算", base), ("7 ディフェンダー", base - 20)))
                self.assertEqual(damage["modifiers"], ((7, defender_card, -20),))
                self.assertEqual(damage["amount"], amount)  # 途中のマイナス（10 - 20）は、最後に 0

    def test_exactly_hp_knocks_out(self):
        """ガーディ（HP60）にダメージ 40。スペシャルパンチ 40 - 20 = 20 で、ちょうど HP → きぜつ（p.319・p.323）。"""
        state = defended({"card": GROWLITHE, "damage": 40}, "hitmonchan", bench=[PONYTA])
        card = active(state, 0).trainers[0].card
        state, events, damage = attack(state)
        self.assertEqual((damage["amount"], damage["total_damage"]), (20, 60))
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(ko["discarded_trainers"], (card,))
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assertEqual(state.players[0].discard.count(card), 1)

    def test_one_short_of_hp_survives(self):
        state = defended({"card": GROWLITHE, "damage": 30}, "hitmonchan")
        state, events, damage = attack(state)
        self.assertEqual(damage["total_damage"], 50)
        self.assertNotIn("knock_out", [e["kind"] for e in events])

    def test_two_defenders(self):
        state = defended(GROWLITHE, "hitmonchan", defenders=2)
        cards = [t.card for t in active(state, 0).trainers]
        _, _, damage = attack(state)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 40), ("7 ディフェンダー", 20), ("7 ディフェンダー", 0)))
        self.assertEqual((damage["amount"], damage["modifiers"]), (0, tuple((7, c, -20) for c in cards)))

    def test_weakness_then_defender(self):
        """ガーディ（弱点 水）にヒトデマンのひらてうち 20: 3 段階で 40、7 段階で 20。"""
        state = defended(GROWLITHE, "staryu")
        _, _, damage = attack(state)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 20), ("3 弱点", 40), ("7 ディフェンダー", 20)))
        self.assertEqual((damage["amount"], damage["weakness"]), (20, True))

    def test_resistance_then_defender_keeps_negative_values(self):
        """ディグダ（抵抗力 雷 -30）にビリリダマのたいあたり 10: 10 → -20 → -40 → 0（ダメージを受けなかった）。"""
        state = defended(DIGLETT, "voltorb")
        _, _, damage = attack(state)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 10), ("4 抵抗力", -20), ("7 ディフェンダー", -40)))
        self.assertEqual((damage["amount"], damage["resistance"]), (0, True))
        self.assertNotIn("stopped_after_step_2", damage)

    def test_resistance_pluspower_and_defender(self):
        """ドードー（抵抗力 闘 -30）にエビワラーのスペシャルパンチ 40 + プラスパワー 2 枚: 40 → 10 → 20 → 30 → 10。"""
        state = defended(DODUO, "hitmonchan", their_hand=[PLUSPOWER, PLUSPOWER])
        for card in hand(state, 1, PLUSPOWER):
            state = apply_command(state, PlayTrainer(1, card))
        _, _, damage = attack(state)
        self.assertEqual([label for label, _ in damage["steps"]],
                         ["1 基本となる計算", "4 抵抗力", "5 プラスパワー", "5 プラスパワー", "7 ディフェンダー"])
        self.assertEqual([value for _, value in damage["steps"]], [40, 10, 20, 30, 10])
        self.assertEqual(damage["amount"], 10)

    def test_pluspower_then_defender(self):
        """基本 30 + プラスパワー 10 - ディフェンダー 20 = 20（弱点・抵抗力なし。5 段階のあとに 7 段階）。"""
        state = defended(GROWLITHE, "ponyta", their_hand=[PLUSPOWER])
        pluspower = hand(state, 1, PLUSPOWER)[0]
        state = apply_command(state, PlayTrainer(1, pluspower))
        defender_card = active(state, 0).trainers[0].card
        _, _, damage = attack(state)
        self.assertEqual(damage["steps"], (("1 基本となる計算", 30), ("5 プラスパワー", 40), ("7 ディフェンダー", 20)))
        self.assertEqual(damage["modifiers"], ((5, pluspower, 10), (7, defender_card, -20)))
        self.assertEqual(damage["amount"], 20)

    def test_two_pluspowers_and_one_defender_with_weakness(self):
        """ガーディ（弱点 水）にひらてうち 20 + プラスパワー 2 枚: 20 → 40 → 50 → 60 → 40。"""
        state = defended(GROWLITHE, "staryu", their_hand=[PLUSPOWER, PLUSPOWER])
        for card in hand(state, 1, PLUSPOWER):
            state = apply_command(state, PlayTrainer(1, card))
        _, _, damage = attack(state)
        self.assertEqual([value for _, value in damage["steps"]], [20, 40, 50, 60, 40])

    def test_defender_does_not_change_damage_dealt(self):
        """ディフェンダーは受けるダメージだけを変える。つけたポケモンがワザを使っても、与えるダメージは変わらない。"""
        state = build_test_state([{"active": {"card": MACHOP, "energy": [FIGHTING]}, "hand": [DEFENDER]}, {"active": GROWLITHE}])
        state = play_defender(state)
        state, _, damage = attack(state, player=0, index=0)
        self.assertEqual((damage["amount"], damage["steps"]), (20, (("1 基本となる計算", 20),)))
        self.assertNotIn("modifiers", damage)

    def test_last_prize_wins_and_the_card_goes_with_the_pokemon(self):
        state = defended({"card": RATTATA, "damage": 10}, "hitmonchan", their_prizes=1)
        card = active(state, 0).trainers[0].card
        state, _, damage = attack(state)  # 40 - 20 = 20 → コラッタ（HP30）きぜつ
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 1))
        self.assertEqual(state.players[0].discard.count(card), 1)
        self.assertEqual(check_invariants(state), [])


# ---------------------------------------------------------------- 有効期限（13.4）


class DefenderExpiryTest(RejectsMixin, unittest.TestCase):
    """次の相手の番の終わりにトラッシュする（p.257）。効果は、ついている間だけ。"""

    def setUp(self):
        self.state = build_test_state([
            {"active": GROWLITHE, "bench": [SEEL], "hand": [DEFENDER, PLUSPOWER, SWITCH]},
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING] * 3}},
        ])  # エビワラーのスペシャルパンチ 40 では、ガーディ（HP60）もパウワウ（HP60）もきぜつしない
        self.turn = self.state.turn_number
        self.card = hand(self.state, 0, DEFENDER)[0]

    def discards(self, state):
        return [(e["card"], e["turn"], e["player"]) for e in state.log if e["kind"] == "discard_attached_trainer"]

    def test_timeline(self):
        state = play_defender(self.state)
        self.assertEqual(active(state, 0).trainers, [AttachedTrainer(self.card, 0, self.turn + 1)])  # 使った直後
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.turn_number, state.current_player), (self.turn + 1, 1))
        self.assertEqual(len(active(state, 0).trainers), 1)  # 自分の番の終わりではトラッシュしない
        self.assertEqual(self.discards(state), [])  # 相手の番の始まりもついたまま
        state, _, damage = attack(state)  # 相手の番の攻撃: 40 - 20
        self.assertEqual(damage["amount"], 20)
        self.assertEqual(self.discards(state), [(self.card, self.turn + 1, 0)])  # 相手の番の終わりにトラッシュ
        self.assertIn(self.card, state.players[0].discard)
        self.assertEqual((state.turn_number, state.current_player), (self.turn + 2, 0))  # 次の自分の番
        self.assertEqual(active(state, 0).trainers, [])
        state = apply_command(state, EndTurn(0))
        _, _, damage = attack(state)  # もう効果はない
        self.assertEqual((damage["amount"], damage["steps"]), (40, (("1 基本となる計算", 40),)))

    def test_discard_event_order_at_the_end_of_the_opponent_turn(self):
        """相手の番の終わりのトラッシュは、ターン終了のログ（turn_end）とポケモンチェックの前（p.309・p.323）。"""
        state = apply_command(play_defender(self.state), EndTurn(0))
        start = len(state.log)
        state = apply_command(state, EndTurn(1))  # 相手がワザを使わずに番を終える
        kinds = [e["kind"] for e in state.log[start:]]
        self.assertEqual(kinds[:4], ["end_turn_without_attack", "discard_attached_trainer", "turn_end", "pokemon_check"])
        self.assertEqual(self.discards(state), [(self.card, self.turn + 1, 0)])

    def test_on_the_bench(self):
        bench = self.state.players[0].bench[0].pokemon_id
        state = apply_command(play_defender(self.state, target=bench), EndTurn(0))
        state, _, damage = attack(state)  # バトル場のガーディには効果がない
        self.assertEqual(damage["amount"], 40)
        self.assertEqual(self.discards(state), [(self.card, self.turn + 1, 0)])  # ベンチからトラッシュ
        self.assertEqual(state.players[0].bench[0].trainers, [])

    def test_retreat_moves_the_card(self):
        # にげるエネルギー 0 のコラッタとドードーで確かめる。相手はポニータのほのおのしっぽ 30（炎）
        state = build_test_state([{"active": RATTATA, "bench": [DODUO], "hand": [DEFENDER]},
                                  {"active": {"card": PONYTA, "energy": [FIRE, FIRE]}}])
        card = state.players[0].hand[0]
        state = play_defender(state)
        pokemon_id = active(state, 0).pokemon_id
        state = apply_command(state, Retreat(0, (), state.players[0].bench[0].card))
        moved = state.players[0].bench[0]
        self.assertEqual((moved.pokemon_id, [t.card for t in moved.trainers]), (pokemon_id, [card]))
        # 同じ番にもどれば効果がある（カードはついたまま。p.311・p.313）
        back = apply_command(state, Retreat(0, (), moved.card))
        self.assertEqual([t.card for t in active(back, 0).trainers], [card])
        _, _, damage = attack(apply_command(back, EndTurn(0)))
        self.assertEqual(damage["amount"], 10)  # コラッタにほのおのしっぽ 30 - 20
        # ベンチにいたまま相手の番になると、バトル場のドードーには効果がなく、相手の番の終わりにベンチからトラッシュ
        state = apply_command(state, EndTurn(0))
        state, _, damage = attack(state)
        self.assertEqual(damage["amount"], 30)
        self.assertEqual([e["card"] for e in state.log if e["kind"] == "discard_attached_trainer"], [card])

    def test_switch_moves_the_card(self):
        state = play_defender(self.state)
        state = apply_command(state, PlayTrainer(0, hand(state, 0, SWITCH)[0]))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
        self.assertEqual([t.card for t in state.players[0].bench[0].trainers], [self.card])
        state, _, damage = attack(apply_command(state, EndTurn(0)))
        self.assertEqual(damage["amount"], 40)  # 新しいバトル場のパウワウには効果がない
        self.assertEqual(self.discards(state), [(self.card, self.turn + 1, 0)])

    def test_pluspower_and_defender_on_the_same_pokemon_expire_separately(self):
        state = play_defender(self.state)
        pluspower = hand(state, 0, PLUSPOWER)[0]
        state = apply_command(state, PlayTrainer(0, pluspower))
        self.assertEqual([(t.card, t.discard_at_end_of_turn) for t in active(state, 0).trainers],
                         [(self.card, self.turn + 1), (pluspower, self.turn)])
        state = apply_command(state, EndTurn(0))
        self.assertEqual([t.card for t in active(state, 0).trainers], [self.card])  # プラスパワーだけトラッシュ
        self.assertEqual(self.discards(state), [(pluspower, self.turn, 0)])
        state, _, _ = attack(state)
        self.assertEqual(self.discards(state), [(pluspower, self.turn, 0), (self.card, self.turn + 1, 0)])

    def test_both_players_cards_expire_at_the_end_of_the_same_turn(self):
        """相手が自分の番に使ったプラスパワーと、こちらのディフェンダーは、同じ相手の番の終わりにトラッシュする。

        番のプレイヤーの場、相手の場の順（v0.2c の実装上の決め事。トラッシュに順番はない p.312）。
        """
        state = build_test_state([
            {"active": GROWLITHE, "hand": [DEFENDER]},
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING] * 3}, "hand": [PLUSPOWER]},
        ])
        defender = state.players[0].hand[0]
        state = apply_command(play_defender(state), EndTurn(0))
        pluspower = hand(state, 1, PLUSPOWER)[0]
        state = apply_command(state, PlayTrainer(1, pluspower))
        state, _, damage = attack(state)
        self.assertEqual(damage["amount"], 30)  # 40 + 10 - 20
        turn = state.turn_number - 1
        self.assertEqual(self.discards(state), [(pluspower, turn, 1), (defender, turn, 0)])

    def test_game_ends_before_the_opponent_turn_ends(self):
        """相手の番の最初に山札がなくて負けると、番の終わりは来ないので、ディフェンダーはついたまま（p.309・p.311）。"""
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP, "deck": []}])
        state = apply_command(play_defender(state), EndTurn(0))
        self.assertEqual((state.phase, state.result.winner), (Phase.GAME_OVER, 0))
        self.assertEqual(len(active(state, 0).trainers), 1)
        self.assertEqual(check_invariants(state), [])

    def test_game_won_with_the_card_on_the_bench(self):
        """ベンチのポケモンについたまま、相手が最後のサイドを取って勝つ: 対戦が終わり、カードは残る。"""
        state = build_test_state([
            {"active": {"card": RATTATA, "damage": 20}, "bench": [PONYTA], "hand": [DEFENDER]},
            {"active": {"card": HITMONCHAN, "energy": [FIGHTING] * 3}, "prizes": 1},
        ])
        card = state.players[0].hand[0]
        state = apply_command(play_defender(state, target=state.players[0].bench[0].pokemon_id), EndTurn(0))
        state, _, _ = attack(state)
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual([t.card for t in state.players[0].bench[0].trainers], [card])
        self.assertEqual(check_invariants(state), [])

    def test_no_randomness(self):
        fingerprint = rng_fingerprint(self.state.rng)
        state = apply_command(play_defender(self.state), EndTurn(0))
        state, _, _ = attack(state)
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)


class KnockOutWithDefendersTest(unittest.TestCase):
    """ディフェンダーをつけたポケモンがきぜつしたら、ついていたカードもいっしょにトラッシュする（p.323）。"""

    def test_attached_card_is_discarded_once(self):
        state = defended({"card": DRATINI, "damage": 30}, "ponyta", defenders=1, bench=[PONYTA])
        cards = [t.card for t in active(state, 0).trainers]
        state, events, _ = attack(state)  # 30 - 20 = 10 → ミニリュウ（HP40）きぜつ
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(ko["discarded_trainers"], tuple(cards))
        state = apply_command(state, TakePrize(1, 0))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual([e for e in state.log if e["kind"] == "discard_attached_trainer"], [])  # 期限の処理と重ならない
        for card in cards:
            self.assertEqual(state.players[0].discard.count(card), 1)
        self.assertEqual(check_invariants(state), [])

    def test_two_defenders_knocked_out_together(self):
        state = defended({"card": DRATINI, "damage": 30}, "hitmonchan", defenders=2, bench=[PONYTA])
        _, events, damage = attack(state)  # 40 - 40 = 0 → きぜつしない（HP40 にダメージ 30）
        self.assertEqual(damage["amount"], 0)
        self.assertNotIn("knock_out", [e["kind"] for e in events])
        state = defended({"card": DRATINI, "damage": 30}, "hitmonchan", defenders=2, bench=[PONYTA], their_hand=[PLUSPOWER])
        cards = [t.card for t in active(state, 0).trainers]
        state = apply_command(state, PlayTrainer(1, hand(state, 1, PLUSPOWER)[0]))
        state, events, damage = attack(state)  # 40 + 10 - 40 = 10 → きぜつ
        self.assertEqual(damage["amount"], 10)
        self.assertEqual(next(e for e in events if e["kind"] == "knock_out")["discarded_trainers"], tuple(cards))
        for card in cards:
            self.assertEqual(state.players[0].discard.count(card), 1)


# ---------------------------------------------------------------- コインのワザ（9.3）


class CoinAttackAgainstDefenderTest(unittest.TestCase):
    """ドードーの「みだれづき」（p.231）で、ディフェンダーをつけたポケモンを攻撃する。プレイヤー 1 が自分の番（4 番）に
    ディフェンダーを使い、プレイヤー 0 の番（5 番）にドードーがワザを使う。"""

    def setup(self, defender_card, *sides, pluspowers=0):
        state = build_test_state([
            {"active": {"card": DODUO, "energy": [FIRE]}, "hand": [PLUSPOWER] * pluspowers},
            {"active": defender_card, "hand": [DEFENDER]},
        ], current_player=1, turn_number=4, pool=TEST_POOL)
        state = apply_command(play_defender(state, player=1), EndTurn(1))
        for card in hand(state, 0, PLUSPOWER):
            state = apply_command(state, PlayTrainer(0, card))
        return with_coin_results(state, *sides)

    def test_heads_and_defender(self):
        cases = (((T, T), (("1 基本となる計算", 0),), 0, True), ((H, T), (("1 基本となる計算", 10), ("7 ディフェンダー", -10)), 0, False),
                 ((H, H), (("1 基本となる計算", 20), ("7 ディフェンダー", 0)), 0, False))
        for sides, steps, amount, stopped in cases:
            with self.subTest(sides=sides):
                state = self.setup(STARYU, *sides)
                expected = copy_rng(state.rng)
                expected.getrandbits(1), expected.getrandbits(1)
                state, _, damage = attack(state, player=0, index=0)
                self.assertEqual((damage["steps"], damage["amount"], damage.get("stopped_after_step_2", False)), (steps, amount, stopped))
                if stopped:
                    self.assertNotIn("modifiers", damage)  # 2 段階で終えたので、7 段階のディフェンダーも計算しない
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))  # 乱数はコイン 2 枚ぶんだけ

    def test_pluspower_and_defender(self):
        state = self.setup(STARYU, H, H, pluspowers=1)
        _, _, damage = attack(state, player=0, index=0)
        self.assertEqual([value for _, value in damage["steps"]], [20, 30, 10])
        self.assertEqual(damage["amount"], 10)

    def test_resistance_pluspowers_and_defender(self):
        """無色に抵抗力 -30 のテスト専用のカード: 20 → -10 → 0 → 10 → -10 → 0。"""
        state = self.setup(RESISTANT, H, H, pluspowers=2)
        _, _, damage = attack(state, player=0, index=0)
        self.assertEqual([value for _, value in damage["steps"]], [20, -10, 0, 10, -10])
        self.assertEqual(damage["amount"], 0)


# ---------------------------------------------------------------- 状態の保存と不変条件（11・12）


class DefenderStateTest(unittest.TestCase):
    def setUp(self):
        self.state = play_defender(build_test_state([
            {"active": GROWLITHE, "bench": [PONYTA], "hand": [DEFENDER, PLUSPOWER]}, {"active": MACHOP},
        ]))
        self.state = apply_command(self.state, PlayTrainer(0, hand(self.state, 0, PLUSPOWER)[0]))
        self.defender, self.pluspower = active(self.state, 0).trainers

    def test_format_4_records_source_owner_target_and_expiry(self):
        data = full(self.state)["players"][0]["active"]
        self.assertEqual(data["pokemon_id"], active(self.state, 0).pokemon_id)
        self.assertEqual(data["trainers"], [
            {"card": self.defender.card, "card_id": DEFENDER, "player": 0, "discard_at_end_of_turn": self.state.turn_number + 1},
            {"card": self.pluspower.card, "card_id": PLUSPOWER, "player": 0, "discard_at_end_of_turn": self.state.turn_number},
        ])
        for version in (1, 2, 3):  # ついているカードを表せない形式は、黙って落とさずに拒否する
            with self.assertRaises(ValueError):
                state_to_dict(self.state, format_version=version)

    def test_card_in_use_needs_format_3_or_later(self):
        state = build_test_state([{"active": GROWLITHE, "hand": [DEFENDER]}, {"active": MACHOP}])
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        for version in (1, 2):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        self.assertEqual(state_to_dict(state, format_version=3)["trainer_in_use"]["card_id"], DEFENDER)

    def test_copies_keep_and_do_not_share(self):
        after = apply_command(self.state, EndTurn(0))
        for copied in (self.state.clone(), copy.deepcopy(self.state), pickle.loads(pickle.dumps(self.state))):
            self.assertEqual(full(copied), full(self.state))
            self.assertEqual(full(apply_command(copied, EndTurn(0))), full(after))
            active(copied, 0).trainers.clear()
            self.assertEqual(len(active(self.state, 0).trainers), 2)

    def test_broken_expiry_is_detected(self):
        too_long = self.state.clone()
        active(too_long, 0).trainers[0] = dataclasses.replace(self.defender, discard_at_end_of_turn=self.state.turn_number + 2)
        self.assertTrue(any("1 番より先" in p for p in check_invariants(too_long)))
        wrong_turn = self.state.clone()  # ディフェンダーを相手の番に使ったことになる期限
        active(wrong_turn, 0).trainers[0] = dataclasses.replace(self.defender, discard_at_end_of_turn=self.state.turn_number)
        self.assertTrue(any("使った番" in p for p in check_invariants(wrong_turn)))
        stale = apply_command(self.state, EndTurn(0))
        stale.turn_number += 2
        stale.current_player = 1
        self.assertTrue(any("有効期限" in p for p in check_invariants(stale)))

    def test_turn_order_is_checked(self):
        broken = self.state.clone()
        broken.current_player = 1  # 3 番は先攻（プレイヤー 0）の番
        self.assertTrue(any("番のプレイヤー" in p for p in check_invariants(broken)))


if __name__ == "__main__":
    unittest.main()
