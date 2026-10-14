"""R団のファイヤーのポケモンパワー「ふしちょう」（v0.12。盤面を直接作るテスト）。

最新の説明（『ポケモンカードオフィシャルブック2000』p.82）: 「この力は、このカードが「きぜつ」したとき、使える。このカードをトラッシュから
とり出し、相手プレイヤーに見せてから、手札に加える。このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」するとき、この力は使えない。」
解説（p.82）: 「トラッシュからもどってくるとはいっても、きぜつすることに変わりはありませんので、相手はサイドカードを1枚とることができます。」
一般規定: p.311（特殊能力を使うかはプレイヤーが決める・決められたときにしか使用を宣言できないもの・勝ち負け「そこで…終了」）、p.322
（持続する効果は場をはなれたら消え、復活しない）、p.323（きぜつの処理: トラッシュ → サイド → バトル場に出す）、p.325（同じタイミングの
ことがらの順番）、p.48（かがくへんかガス）。kyuura の記録 id: PMCG5-020・NEO-2000-OFFICIAL-RULES・knockout_timing。

裁定（P1〜P30）は docs/phoenix-v0.12.md、仕組みは docs/post-knockout-powers-v0.12.md。原典で決められない順番（P27・P28・P30）は、
結果が変わらないことを確かめて正規化した順番（サイド → 勝ち負けの判定 → （対戦が続くなら）ふしちょう → バトル場に出す）で処理し、テストは
その順番を「ルール」としてではなく実装の形として確かめる。P19（ガスの発生源もいっしょにきぜつ）は、対応カードでは先に止めているので
起こらない（関数を直接呼んで、エンジンの不具合として止まることだけを確かめる）。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, AttackKey, EndTurn, IllegalActionError, Phase, PlayBasicToBench, PowerKey, ResolveDecision, TakePrize, UseAttack,
    UsePokemonPower, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import POST_KNOCKOUT_POWER
from kyuura_engine.effects import AttackEffect, AttackEntry, ReturnToHandOnKnockOut, SELF, deal_attack_damage, post_knockout_power
from kyuura_engine.resolution.kernel import Resolution, capture_post_knockout
from kyuura_engine.resolution.questions import OpenQuestion, to_error


def _post_knockout_candidates(state, knocked):
    """きぜつしたときに使える特殊能力の候補（v0.16b: 解決の基盤のきぜつの処理の窓 ``kernel.capture_post_knockout``。v0.15 までは v0.13 の
    経路の ``engine._post_knockout_candidates``）。原典で決められない場合（P19・P32。コードのない問い）は、コマンドの入口と同じく
    ``RuntimeError``（``questions.to_error``）にする。"""
    try:
        return capture_post_knockout(Resolution(state), knocked)
    except OpenQuestion as question:
        raise to_error(question.key, question.detail, question.error) from None
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    ALAKAZAM, ABRA, DEFENDER, FIRE, GRASS, GRIMER, H, HAUNTER, GASTLY, KADABRA, MACHAMP, MACHOKE, MACHOP, MUK, PONYTA, PSYCHIC,
    ROCKETS_MOLTRES, build_test_state, with_coin_results,
)
from tests.log_audit import serialization_problems

REBIRTH = PowerKey(ROCKETS_MOLTRES, 0)
LATEST = ("この力は、このカードが「きぜつ」したとき、使える。このカードをトラッシュからとり出し、相手プレイヤーに見せてから、手札に加える。"
          "このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」するとき、この力は使えない。")
PRINTED = ("この力は、このカードが「きぜつ」した時だけ、使える。このカードをトラッシュからとり出し、手札に加える。このカードが「ねむり・マヒ・"
           "こんらん」状態のまま「きぜつ」する時、この力は使えない。")


def full(state):
    return state_to_dict(state, format_version=9)


def ko_board(moltres=None, *, attacker=None, moltres_bench=(MACHOP,), attacker_bench=(MACHOP,), prizes=6, turn=5, **extra):
    """プレイヤー 0 のポニータ（ほのおのしっぽ 30）が、プレイヤー 1 の R団のファイヤー（ダメージ 30。30 できぜつ）を攻撃する盤面。"""
    spec = {"card": ROCKETS_MOLTRES, "damage": 30, "energy": [FIRE, FIRE]}
    spec.update(moltres or {})
    return build_test_state([
        {"active": attacker or {"card": PONYTA, "energy": [FIRE, FIRE]}, "bench": list(attacker_bench), "prizes": prizes, **extra},
        {"active": spec, "bench": list(moltres_bench)},
    ], current_player=0, turn_number=turn)


def attack_and_take_prize(state, attack_index=1):
    state = apply_command(state, UseAttack(0, attack_index))
    if state.phase is Phase.TAKE_PRIZE:
        state = apply_command(state, TakePrize(state.decision.player, 0))
    return state


def answer(state, use):
    d = state.decision
    return apply_command(state, ResolveDecision(d.player, d.id, d.options if use else ()))


def kinds_since(state, index):
    return [e["kind"] for e in state.log[index:]]


class RegistrationTest(unittest.TestCase):
    def test_registered_as_a_declared_power(self):
        """宣言して使う特殊能力（P1。「使える」。p.311）。印刷の文面（kyuura の写し）で照合し、最新の説明（p.82）にしたがう。"""
        entry = DEFAULT_EFFECTS.power_entry(ROCKETS_MOLTRES, 0)
        self.assertIsInstance(entry.effect, ReturnToHandOnKnockOut)
        self.assertTrue(entry.effect.declared)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ふしちょう", PRINTED, LATEST, "P43 p.82"))
        self.assertEqual(load_card_pool().get(ROCKETS_MOLTRES).powers[0].text_ja, PRINTED)
        self.assertTrue(load_card_pool().is_playable(ROCKETS_MOLTRES))

    def test_cannot_be_used_while_in_play(self):
        """決められたとき（このカードが「きぜつ」したとき）以外は使えない（P4。p.311「決められたときにしか使用を宣言できないもの」）。
        拒否で状態・乱数・ログは変わらない。かがくへんかガスがはたらいていれば先に POWER_SUPPRESSED（v0.8 の順番）。"""
        state = build_test_state([{"active": ROCKETS_MOLTRES, "bench": [MACHOP]}, {"active": MACHOP}], turn_number=3)
        before = full(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_NOT_USABLE_NOW")
        self.assertEqual(full(state), before)
        gas = build_test_state([{"active": ROCKETS_MOLTRES, "bench": [{"card": MUK, "evolved_from": GRIMER}]}, {"active": MACHOP}],
                               turn_number=5)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(gas, UsePokemonPower(0, gas.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_SUPPRESSED")


class OfferTest(unittest.TestCase):
    """きぜつの処理のあとに、使うかを持ち主が決める（P1〜P4・P20・P21・P27・P28）。"""

    def test_after_prize_before_promotion(self):
        """相手のワザできぜつ（P5）→ トラッシュ（P20）→ 相手がサイドを取る（P27。p.82 の解説）→ 対戦が続くので、持ち主に決定 → 答えのあと
        バトル場に出す（P28）。決定の時点で、カードは持ち主のトラッシュにあり、場にない（P21）。"""
        state = ko_board()
        card = state.players[1].active.card
        state = apply_command(state, UseAttack(0, 1))
        self.assertIs(state.phase, Phase.TAKE_PRIZE)
        self.assertEqual(state.decision.context_value("post_knockout"), ((1, card, ROCKETS_MOLTRES, 0),))
        state = apply_command(state, TakePrize(0, 0))
        d = state.decision
        self.assertEqual((state.phase, d.kind, d.player, d.options, d.min_choices, d.max_choices, d.resume),
                         (Phase.DECISION, POST_KNOCKOUT_POWER, 1, (card,), 0, 1, "post_knockout"))
        self.assertEqual(d.context_value("power"), (ROCKETS_MOLTRES, 0))
        self.assertIn(card, state.players[1].discard)
        self.assertIsNone(state.players[1].active)
        self.assertEqual((state.current_player, state.turn_number, len(state.players[0].prizes)), (0, 5, 5))
        self.assertEqual(check_invariants(state), [])

    def test_use_returns_only_this_card(self):
        """使う: 宣言 → このカードだけをトラッシュから手札へ（P22）。ついていたエネルギー・トレーナーはトラッシュに残る（P23）。同じ uid（P24）。
        サイドは取られたまま（p.82）。そのあとバトル場に出す。乱数は使わない。"""
        state = ko_board({"damage": 50, "trainers": [(DEFENDER, 5)]}, turn=5)  # ディフェンダーで 30 − 20 = 10
        moltres = state.players[1].active
        card, energy, trainer = moltres.card, tuple(moltres.energy), moltres.trainers[0].card
        state = attack_and_take_prize(state)
        start, rng = len(state.log), rng_fingerprint(state.rng)
        hand, discard = list(state.players[1].hand), list(state.players[1].discard)
        state = answer(state, True)
        self.assertEqual(kinds_since(state, start), ["post_knockout_power_declared", "return_to_hand"])
        self.assertEqual(state.log[start + 1]["card"], card)
        self.assertEqual(state.players[1].hand, hand + [card])
        self.assertEqual(sorted(state.players[1].discard), sorted(set(discard) - {card}))
        self.assertTrue(set(energy) | {trainer} <= set(state.players[1].discard))
        self.assertEqual(state.cards[card].card_id, ROCKETS_MOLTRES)
        self.assertEqual(rng_fingerprint(state.rng), rng)
        self.assertEqual(len(state.players[0].prizes), 5)
        self.assertIs(state.phase, Phase.PROMOTE_ACTIVE)
        self.assertEqual(check_invariants(state), [])

    def test_decline_keeps_the_card_in_the_trash(self):
        """使わない（P2。p.311「かならずしも特殊能力の使用を宣言する必要はありません」）: カードはトラッシュに残る。"""
        state = attack_and_take_prize(ko_board())
        card = state.decision.options[0]
        start = len(state.log)
        state = answer(state, False)
        self.assertEqual(kinds_since(state, start), ["post_knockout_power_declined"])
        self.assertIn(card, state.players[1].discard)
        self.assertNotIn(card, state.players[1].hand)

    def test_recovered_card_can_be_played_again_without_old_damage_or_effects(self):
        """手札にもどったカードは、持ち主の番に、ふつうにベンチに出せる（P26）。ダメージ・特殊状態・持続する効果はない（P25。p.322）。"""
        state = ko_board({"poison": 10, "retaliation": 4})
        card = state.players[1].active.card
        state = answer(attack_and_take_prize(state), True)
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:1]))  # バトル場に出す → ワザを使った番が終わる
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))
        state = apply_command(state, PlayBasicToBench(1, card))
        pokemon = next(pk for pk in state.players[1].bench if pk.card == card)
        self.assertEqual((pokemon.damage, pokemon.conditions.names(), pokemon.persistent_effects, pokemon.energy), (0, (), (), []))
        self.assertEqual(check_invariants(state), [])

    def test_offered_again_after_a_second_knock_out(self):
        """同じカードが再び場に出て、再びきぜつしたら、また使える（P12。回数の制限はない。p.323「何度でも」）。"""
        from tests.test_moltres_games_v0_12 import GOLDEN_SEED, play_game
        state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        answers = [e for e in state.log if e["kind"] in ("post_knockout_power_declared", "post_knockout_power_declined")]
        self.assertEqual(len({e["card"] for e in answers}), 1)
        self.assertEqual([e["kind"] for e in answers], ["post_knockout_power_declared", "post_knockout_power_declined"])


class CauseTest(unittest.TestCase):
    """きぜつの原因は問わない（P5〜P10。最新の説明は「「きぜつ」したとき」だけ）。"""

    def test_knocked_out_by_counterattack_on_its_own_turn(self):
        """自分の番に、自分のワザのあと相手の「はんげき」（特殊能力のダメージ）できぜつ（P8）: 番のプレイヤーが決める。「ほのおのかべ」の
        効果は与えない（相手の「はんげき」で HP 以上。persistent_effect_skipped）。"""
        state = build_test_state([
            {"active": {"card": ROCKETS_MOLTRES, "damage": 50, "energy": [FIRE] * 3}, "bench": [MACHOP]},
            {"active": {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}, "bench": [MACHOP]},
        ], turn_number=7)
        card = state.players[0].active.card
        state = apply_command(state, UseAttack(0, 0))
        self.assertIn("persistent_effect_skipped", [e["kind"] for e in state.log])
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.decision.kind, state.decision.player, state.decision.options), (POST_KNOCKOUT_POWER, 0, (card,)))
        state = answer(state, True)
        self.assertIn(card, state.players[0].hand)

    def test_knocked_out_by_its_own_attack(self):
        """自分のワザの自分へのダメージできぜつ（P6・P7）: 使える。R団のファイヤーに自分へのダメージのワザはないので、テスト専用の効果
        （相手に 0・自分に 60）を同じ位置に登録して確かめる。"""
        attack = load_card_pool().get(ROCKETS_MOLTRES).attacks[0]

        class SelfKnockOut(AttackEffect):
            implementation_id = "test_self_knock_out"

            def resolve(self, state, use):
                deal_attack_damage(state, use, SELF, 60)

        effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(ROCKETS_MOLTRES, 0): AttackEntry(SelfKnockOut(), attack.name_ja, attack.text_ja)})
        state = build_test_state([
            {"active": {"card": ROCKETS_MOLTRES, "energy": [FIRE] * 3}, "bench": [MACHOP]},
            {"active": MACHOP, "bench": [MACHOP]},
        ], turn_number=5, effects=effects)
        state = apply_command(state, UseAttack(0, 0))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.decision.kind, state.decision.player), (POST_KNOCKOUT_POWER, 0))

    def test_poison_knock_out_in_the_pokemon_check(self):
        """ポケモンチェックのどくのきぜつ（P9・P16）: 使える。決定は続き（then）を持ち、答えのあと、バトル場に出してポケモンチェックの残り → 次の番。"""
        state = ko_board({"damage": 50, "poison": 10})
        card = state.players[1].active.card
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, TakePrize(0, 0))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.context_value("then")), (POST_KNOCKOUT_POWER, 1, "next_turn"))
        state = answer(state, True)
        self.assertIn(card, state.players[1].hand)
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:1]))
        self.assertEqual((state.phase, state.current_player, state.turn_number), (Phase.MAIN, 1, 6))

    def test_damage_swap_cannot_knock_out(self):
        """ダメージカウンターの移動ではきぜつしない（P10。v0.7 の WOULD_KNOCK_OUT。p.153）ので、「ふしちょう」の場面にならない。"""
        state = build_test_state([
            {"active": {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "damage": 30}, "bench": [{"card": ROCKETS_MOLTRES, "damage": 50}]},
            {"active": MACHOP},
        ], turn_number=7)
        alakazam, moltres = state.players[0].active, state.players[0].bench[0]
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=alakazam.pokemon_id, target=moltres.pokemon_id))
        self.assertEqual(ctx.exception.code, "WOULD_KNOCK_OUT")

    def test_location_is_not_restricted(self):
        """場所の制限はない（P11。ベンチのポケモンがきぜつする処理は対応カードにないので、候補の関数で確かめる）。"""
        state = build_test_state([{"active": MACHOP, "bench": [{"card": ROCKETS_MOLTRES, "damage": 60}]}, {"active": MACHOP}], turn_number=3)
        moltres = state.players[0].bench[0]
        self.assertEqual(_post_knockout_candidates(state, [(0, moltres)]), ((0, moltres.card, ROCKETS_MOLTRES, 0),))


class SpecialConditionTest(unittest.TestCase):
    """「このカードが「ねむり・マヒ・こんらん」状態のまま「きぜつ」するとき、この力は使えない」（P13〜P17）。"""

    def test_asleep_paralyzed_confused_cannot_use(self):
        for condition in ({"sleep": True}, {"paralysis": 4}, {"confusion": True}):
            with self.subTest(condition=condition):
                state = attack_and_take_prize(ko_board(condition))
                self.assertIsNot(state.decision.kind, POST_KNOCKOUT_POWER)
                self.assertIs(state.phase, Phase.PROMOTE_ACTIVE)
                self.assertNotIn("post_knockout_power_declined", [e["kind"] for e in state.log])

    def test_poisoned_can_use(self):
        state = attack_and_take_prize(ko_board({"poison": 10}))
        self.assertEqual(state.decision.kind, POST_KNOCKOUT_POWER)

    def test_condition_at_the_knock_out_is_what_counts(self):
        """きぜつするときの特殊状態で決める（P17）: ワザでねむりになって（きぜつしない）、ポケモンチェックのどくできぜつ → 使えない。ワザの
        ダメージで HP 以上になった相手には、そのワザのねむりは与えない（v0.4d）ので、同じワザできぜつしたら使える。"""
        state = build_test_state([
            {"active": {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, "bench": [MACHOP]},
            {"active": {"card": ROCKETS_MOLTRES, "damage": 40, "poison": 10}, "bench": [MACHOP]},
        ], turn_number=7)
        state = apply_command(state, UseAttack(0, 0))  # あくむ 10 → 50。ねむり。番の終わりのポケモンチェックのどく 10 → 60 できぜつ
        kinds = [e["kind"] for e in state.log]
        self.assertLess(kinds.index("special_condition"), kinds.index("knock_out"))
        self.assertEqual(state.log[kinds.index("knock_out")]["timing"], "pokemon_check")
        self.assertIs(state.phase, Phase.TAKE_PRIZE)
        self.assertIsNone(state.decision.context_value("post_knockout"))
        state = apply_command(state, TakePrize(0, 0))
        self.assertIs(state.phase, Phase.PROMOTE_ACTIVE)
        same_attack = build_test_state([
            {"active": {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, "bench": [MACHOP]},
            {"active": {"card": ROCKETS_MOLTRES, "damage": 50}, "bench": [MACHOP]},
        ], turn_number=7)
        same_attack = attack_and_take_prize(same_attack, 0)
        self.assertEqual(same_attack.decision.kind, POST_KNOCKOUT_POWER)


class GasTest(unittest.TestCase):
    """かがくへんかガス（p.48「…すべての「特殊能力」は使えず、その力も消える」。P18）。"""

    def test_working_gas_on_either_side_blocks(self):
        for side in (0, 1):
            with self.subTest(side=side):
                muk = {"card": MUK, "evolved_from": GRIMER}
                state = ko_board(attacker_bench=[muk] if side == 0 else [MACHOP], moltres_bench=[muk] if side == 1 else [MACHOP], turn=7)
                state = attack_and_take_prize(state)
                self.assertIs(state.phase, Phase.PROMOTE_ACTIVE)

    def test_gas_off_when_muk_is_confused(self):
        """ベトベトンがねむり・マヒ・こんらんなら、かがくへんかガスは消えている（v0.8 の G9〜G11）ので使える（こんらんのベトベトンが
        ワザを使う盤面。こんらんのコインは「おもて」）。"""
        state = ko_board(attacker={"card": MUK, "evolved_from": GRIMER, "energy": [GRASS] * 3, "confusion": True}, turn=7)
        state = with_coin_results(state, H)
        state = attack_and_take_prize(state, 0)  # ヘドロこうげき 30（こんらんのコイン「おもて」）
        self.assertEqual(state.decision.kind, POST_KNOCKOUT_POWER)

    def test_gas_source_knocked_out_at_the_same_time_is_unresolved(self):
        """P19（かがくへんかガスの発生源もいっしょにきぜつ）は原典で決められない。対応カードでは先に止めている（W24・ポケモンチェックの両方の
        きぜつ）ので起こらない。候補の関数を直接呼ぶと、エンジンの不具合として止まる。"""
        state = build_test_state([
            {"active": {"card": ROCKETS_MOLTRES, "damage": 60}},
            {"active": {"card": MUK, "evolved_from": GRIMER, "damage": 70}},
        ], turn_number=5)
        knocked = [(0, state.players[0].active), (1, state.players[1].active)]
        with self.assertRaises(RuntimeError):
            _post_knockout_candidates(state, knocked)

    def test_two_candidates_are_an_engine_error(self):
        """2 匹以上が同時にきぜつして使える場合の順番（p.325）は、対応カードでは起こらない。関数を直接呼ぶと、エンジンの不具合として止まる。"""
        state = build_test_state([{"active": {"card": ROCKETS_MOLTRES, "damage": 60}}, {"active": {"card": ROCKETS_MOLTRES, "damage": 60}}])
        with self.assertRaises(RuntimeError):
            _post_knockout_candidates(state, [(0, state.players[0].active), (1, state.players[1].active)])


class GameEndTest(unittest.TestCase):
    """対戦が終わる場合は決めさせない（P29・P30。p.311「そこで…対戦は終了します」。手札にもどしても勝ち負けは変わらない）。"""

    def test_last_prize(self):
        state = attack_and_take_prize(ko_board(prizes=1))
        self.assertIs(state.phase, Phase.GAME_OVER)
        self.assertNotIn("post_knockout_power_declined", [e["kind"] for e in state.log])
        self.assertIn(state.log[-1]["kind"], ("game_end",))

    def test_last_pokemon(self):
        """ベンチにポケモンがいない（手札のたねポケモンはバトル場に出せない。p.311）。"""
        state = attack_and_take_prize(ko_board(moltres_bench=()))
        self.assertIs(state.phase, Phase.GAME_OVER)
        self.assertEqual(state.result.conditions, ((0, "OPPONENT_CANNOT_FIELD_ACTIVE"),))


class AtomicityAndSaveTest(unittest.TestCase):
    """決定を待つ状態の保存・復元（D5）と、不正な答え（状態・乱数・ログを変えない。C4）。"""

    def decision_state(self):
        return attack_and_take_prize(ko_board())

    def test_invalid_answers_change_nothing(self):
        state = self.decision_state()
        d = state.decision
        before, rng = full(state), rng_fingerprint(state.rng)
        energy = state.players[1].discard[0] if state.players[1].discard[0] != d.options[0] else state.players[1].discard[1]
        for command in (
            ResolveDecision(0, d.id, d.options),  # 決定するのは持ち主
            ResolveDecision(1, d.id + 1, d.options),  # 違う決定
            ResolveDecision(1, d.id, (energy,)),  # ほかのカード
            ResolveDecision(1, d.id, (d.options[0], d.options[0])),
            UsePokemonPower(1, 1, 0), EndTurn(0), PlayBasicToBench(1, state.players[1].hand[0] if state.players[1].hand else 0),
        ):
            with self.subTest(command=command):
                with self.assertRaises(IllegalActionError):
                    apply_command(state, command)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))

    def test_pickle_deepcopy_clone_and_resume(self):
        state = self.decision_state()
        for copied in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
            with self.subTest(kind=type(copied).__name__):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(rng_fingerprint(copied.rng), rng_fingerprint(state.rng))
                for use in (True, False):
                    self.assertEqual(full(answer(copied, use)), full(answer(state, use)))

    def test_serialization_formats(self):
        """決定は形式 2 以上の decision で表す（形式 9 のまま）。形式 1 は ValueError（黙って落とさない）。サイドを取る決定（候補を持つ）も同じ。"""
        prize = apply_command(ko_board(), UseAttack(0, 1))
        for state in (prize, self.decision_state()):
            with self.subTest(phase=state.phase.value):
                with self.assertRaises(ValueError):
                    state_to_dict(state, format_version=1)
                self.assertEqual(serialization_problems(state), [])
        decision = state_to_dict(self.decision_state(), format_version=2)["decision"]
        self.assertEqual((decision["kind"], decision["resume"], decision["context"]),
                         (POST_KNOCKOUT_POWER, "post_knockout", {"power": [ROCKETS_MOLTRES, 0]}))

    def test_invariants_reject_a_broken_decision(self):
        """決定の形が壊れた状態（カードがトラッシュにない・選べるものが違う）は不変条件の違反。"""
        state = self.decision_state()
        card = state.decision.options[0]
        moved = state.clone()
        moved.players[1].discard.remove(card)
        moved.players[1].hand.append(card)
        self.assertTrue(any("トラッシュにない" in p for p in check_invariants(moved)))
        import dataclasses
        other = state.clone()
        other.decision = dataclasses.replace(other.decision, options=(other.players[1].discard[0],) if other.players[1].discard[0] != card
                                             else (other.players[1].discard[1],))
        self.assertNotEqual(check_invariants(other), [])

    def test_power_lookup(self):
        state = ko_board()
        found = post_knockout_power(state, state.players[1].active)
        self.assertEqual(found[0], REBIRTH)
        self.assertIsNone(post_knockout_power(state, state.players[0].active))


if __name__ == "__main__":
    unittest.main()
