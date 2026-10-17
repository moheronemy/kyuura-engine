"""原典で決められない裁定（``UNRESOLVED_…``）が、ちょうど決められない場合だけを止めることの監査（v0.4e。
docs/unresolved-audit-v0.4e.md）。

v0.4e の時点でエンジンが止める 11 件のコード（v0.6 で 1 件加えて 12 件。``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``。
docs/rain-dance-v0.6.md の R13。v0.9 で 2 件加えて 14 件。``UNRESOLVED_EVADED_EFFECT_COIN``（docs/transparency-v0.9.md の T19b）・
``UNRESOLVED_RECOVER_ZERO_ENERGY``（docs/haunter-line-v0.9.md の H4）。v0.10 で 1 件加えて 15 件。
``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT``（docs/counterattack-v0.10.md の C18）。v0.11 で 1 件加えて 16 件。
``UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT``（docs/guts-v0.11.md の G37））のそれぞれについて、

- 止まる場合: 止め方（コマンドの拒否 ``UnsupportedError`` か、対戦を止める ``Phase.HALTED`` か）とコード。拒否なら渡した状態・
  乱数・ログは変わらない（拒否と HALTED を同じものとして扱わない: 拒否は状態を返さず、HALTED は止めた状態を返す）。どちらも
  乱数（コイン）・ダメージ・エネルギーのトラッシュより前に止まる。
- 隣の止まらない場合: 止める条件から 1 つだけ外れた盤面は、いつもどおり処理する（止める範囲が広すぎない）。

を確かめる。v0.4a〜v0.4d で加えた進化・持続する効果・強制交代・メガドレインと組み合わせた盤面も入れる。止める条件・分類は
変えていない（原典に新しい根拠は見つからなかった。docs/unresolved-audit-v0.4e.md）。盤面は ``build_test_state`` で直接作る
（1 つの裁定の範囲を確かめるテスト）。切り直しの補償だけは ``new_game`` の中で決まるので、``new_game`` から確かめる。
"""

import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, EvolvePokemon, IllegalActionError, PlayTrainer, ResolveDecision, Retreat, UnsupportedError,
    UseAttack, UsePokemonPower, apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.conditions import paralysis_problem
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import (
    BEEDRILL, BUTTERFREE, CATERPIE, DEFENDER, DEWGONG, DODUO, FEW_BASICS, GRASS, GROWLITHE, H, KAKUNA, METAPOD, PARAS, PLUSPOWER,
    POTION, PONYTA, RATTATA, SEEL, SWITCH, T, VULPIX, WATER, WEEDLE, FIRE, build_test_state, find_seed, uids, with_coin_results,
    BLASTOISE, BULBASAUR, IVYSAUR, SQUIRTLE, VENUSAUR, WARTORTLE, GASTLY, HAUNTER, GRIMER, MUK, PSYCHIC,
    DIGLETT, FIGHTING, HITMONCHAN, LIGHTNING, MACHAMP, MACHOKE, MACHOP, PIKACHU,
    GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, ROCKETS_MOLTRES, ROCKETS_SNORLAX,
)
from tests.test_evolution_v0_4a import test_pool

ALL_CODES = (
    "UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POTION_WITHOUT_DAMAGE", "UNRESOLVED_POTION_UNDAMAGED_TARGET",
    "UNRESOLVED_SWITCH_WITHOUT_BENCH", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER",
    "UNRESOLVED_REPARALYSIS_RECOVERY_TURN", "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED",
    "UNRESOLVED_EVOLUTION_HP", "UNRESOLVED_PREVENTED_COIN_DAMAGE",
    "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH",  # v0.6
    "UNRESOLVED_EVADED_EFFECT_COIN", "UNRESOLVED_RECOVER_ZERO_ENERGY",  # v0.9
    "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT",  # v0.10
    "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT",  # v0.11
    "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT",  # v0.12
    "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE",  # v0.17b
    "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH",  # v0.21（止まる場合と隣の止まらない場合は tests/test_gust_v0_21.py）
    "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK",  # v0.22（止まる場合と隣の止まらない場合は tests/test_computer_search_v0_22.py）
    "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET",  # v0.23（ER10。止まる場合と隣は tests/test_energy_retrieval_v0_23.py）
    "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE",  # v0.23（ER9。止まる場合と隣は tests/test_energy_retrieval_v0_23.py）
    # v0.31: v0.30 まで起こらなかった（コードのない）5 件を停止コードにした。止まる場合と隣の止まらない場合は tests/test_held_cards_v0_31_stops.py
    "UNRESOLVED_TRANSPARENCY_COIN_ORDER", "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS", "UNRESOLVED_KO_PREVENTION_ORDER",
    "UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT", "UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER",
    # v0.31: HC1〜HC10（docs/held-cards-v0.31.md）。止まる場合と隣の止まらない場合は tests/test_held_cards_v0_31_stops.py
    "UNRESOLVED_DISCARD_ENERGY_TIMING", "UNRESOLVED_DESTINY_BOND_KNOCKOUT", "UNRESOLVED_PREVENTED_EFFECT_COIN",
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS", "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO", "UNRESOLVED_DISCARD_DECK_SHORT",
    "UNRESOLVED_ATTACH_FROM_DISCARD_ZERO", "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE", "UNRESOLVED_COPIED_ATTACK",
    "UNRESOLVED_ENERGY_BURN_TRANSFER",
    # v0.32: CD4（docs/bench-search-counter-drain-v0.32.md）。止まる場合と隣の止まらない場合は tests/test_bench_search_counter_drain_v0_32.py の
    # CounterDamageTest（test_meditate_stops_when_the_reading_matters・test_meditate_counts_the_defending_pokemon）
    "UNRESOLVED_OPPONENT_POKEMON_COUNTERS",
    # v0.34: TP3・NK5（docs/barrier-resume-coin-bonus-v0.34.md）。止まる場合と隣の止まらない場合は tests/test_barrier_resume_coin_bonus_v0_34.py の
    # SpecialPoisonTest（test_normal_poison_to_special_is_unresolved・test_same_special_poison_is_not_stacked）・GrowlTest（test_bench_target_is_unresolved・
    # test_only_this_card_and_expires_at_the_start_of_the_next_turn）
    "UNRESOLVED_SPECIAL_POISON_OVERWRITE", "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET",
    # v0.36: AC6・RD9（docs/sand-attack-retreat-lock-v0.36.md）。止まる場合と隣の止まらない場合は tests/test_sand_attack_retreat_lock_v0_36.py の
    # AttackCheckTest（test_confused_pokemon_stops_before_the_coin・test_heads_continues_and_tails_fails_the_attack）・DeckReturnTest
    # （test_knockout_in_the_same_attack_stops_before_the_declaration・test_heads_returns_the_pokemon_and_attached_cards_after_damage）
    "UNRESOLVED_ATTACK_CHECK_CONFUSION", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT",
    # v0.37: JS1（docs/fifteen-reused-effects-v0.37.md）。止まる場合と隣の止まらない場合は tests/test_fifteen_reused_effects_v0_37.py の
    # EarthquakeTest（test_stops_when_weakness_or_resistance_would_change_the_damage・test_proceeds_when_both_readings_give_the_same_damage）
    "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE",
    # v0.38: GK1（docs/bench-switch-combined-v0.38.md）。止まる場合と隣の止まらない場合は tests/test_bench_switch_combined_v0_38.py の
    # RamTest（test_damage_trigger_stops_before_the_declaration・test_proceeds_without_a_damage_trigger）
    "UNRESOLVED_DAMAGE_TRIGGER_TIMING",
    # v0.39: GS1（docs/selfdestruct-spread-count-v0.39.md）。止まる場合（0 匹の答え）と隣の止まらない場合（1 匹以上）は
    # tests/test_selfdestruct_spread_count_v0_39.py の GigaSparkTest
    "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE",
    # v0.40: SG1（docs/count-condition-switch-return-v0.40.md）。止まる場合（すごむの効果を与えたポケモンを突風でもどす答え・それしか選べない
    # 突風）と隣の止まらない場合（ほかの控えを選ぶ答え）は tests/test_count_condition_switch_return_v0_40.py の IntimidateTest
    "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED",
    # v0.41: CX1（docs/heal-counter-status-v0.41.md）。止まる場合（相手が「ワザをうけない」状態・「とうめい」でダメージカウンターをのせる・取り替える
    # 効果を受けない）と隣の止まらない場合（移す・取り替えるカウンターがない・数が同じ）は tests/test_heal_counter_status_v0_41.py の
    # CounterShiftTest・SwapTest
    "UNRESOLVED_COUNTER_TRANSFER_PROTECTED",
    # v0.42: PW1・PW2（docs/power-decisions-v0.42.md）。止まる場合（相手に控えがいないときのかおりのわな・手札がないときのぶっしつこうかん）と隣の止まらない
    # 場合（控えが 1 匹・手札が 1 枚）は tests/test_power_decisions_v0_42.py の SweetTrapTest・MatterExchangeTest
    "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH",
    "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND",
    # v0.43: PW3・PW4（docs/declared-entry-powers-v0.43.md）。止まる場合（ようぶんきゅうしゅうの 0 枚・つけかえるカードがない・てしたをよぶのベンチに空きがない・
    # 山札にたねポケモンがない・0 枚、しんかのひかりの山札に進化カードがない、つきのちからでわるいカイリューを重ねる）と隣の止まらない場合（1 枚・空きが 1 つ・
    # 進化カードが 1 枚・ほかの進化カード）は tests/test_declared_entry_powers_v0_43.py の SoakUpTest・SummonMinionsTest・EvolutionaryLightTest・
    # MoonPowerRouteTest
    "UNRESOLVED_POWER_ZERO_CARDS",
    "UNRESOLVED_ENTRY_POWER_DURING_ATTACK",
    # v0.44: FC1・TR1（docs/search-evolution-once-attacks-v0.44.md。GV1 は v0.44 ではコードのない問い。v0.45 で停止コードを付けた）。止まる場合（てじなで山札の
    # 基本エネルギーカードがもどす枚数より少ない（1 枚以上）・ラッキーたまごの手札が 0・1 枚、場にサカキのポケモンがいないときのサカキ）と隣の止まらない場合
    # （足りる・0 枚・手札が 2 枚・サカキのポケモンが 1 匹）は tests/test_search_evolution_once_attacks_v0_44.py
    "UNRESOLVED_STATED_CARDS_SHORT",
    "UNRESOLVED_TRAINER_WITHOUT_TARGET",
    # v0.45: GV1（docs/conditional-damage-energy-v0.45.md。v0.44 はコードのない問い）。止まる場合（つきのちからで、この番に場に出してサカキの許可を受けた
    # サカキのコイキングにサカキのギャラドスを重ねる）と隣の止まらない場合（前の番から場にいるサカキのコイキング）は
    # tests/test_conditional_damage_energy_v0_45.py の Gv1Test
    "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK",
    # v0.45: AC13（v0.36 の docs/sand-attack-retreat-lock-v0.36.md。v0.36〜v0.44 は対応カードで起こらず RuntimeError。v0.45 のスミをかける（次の相手の番から
    # 消えない手順 4 の効果）で起こる）。止まる場合（手順 4 の効果が 2 つ）と隣の止まらない場合（1 つ）は tests/test_conditional_damage_energy_v0_45.py の
    # LastingAttackCheckTest
    "UNRESOLVED_MULTIPLE_ATTACK_CHECKS",
    # v0.46: CP1・CP2（docs/continuous-powers-v0.46.md）。止まる場合（［くつろぐかおり］がバトル場にあり、返す効果（こうらがえし）のダメージを半分にするかで
    # 結果が変わる・少なくする数と増やす数の当てはめ方でトラッシュしてよい数が変わる「にげる」）と隣の止まらない場合（ほのおのかべの 10 は半分にしても 10・
    # どちらの読み方でも足りる数）は tests/test_continuous_powers_v0_46.py の CalmingAromaTest・RetreatCostTest
    "UNRESOLVED_CALMING_AROMA_RETALIATION",
    "UNRESOLVED_RETREAT_COST_FLOOR",
    # v0.47: PF1・PF2・PF3・KA1（docs/fossil-hidden-info-v0.47.md）。止まる場合（手札にたねポケモンがなく、なにかの化石がある対戦準備・なにかの化石を最初のポケモンと
    # して出す・バトル場のなにかの化石の「にげる」・ポケモン育て屋さんで場のなにかの化石に 2 進化カード・どく状態のカブトのポケモンチェック）と隣の止まらない場合
    # （ポケモンいれかえ・ほかの組を選ぶ育て屋さん・［なぞのかべ］とどく）は tests/test_fossil_hidden_info_v0_47.py の PlayAsPokemonTest・KabutoArmorTest
    "UNRESOLVED_PLAY_AS_POKEMON_SETUP",
    "UNRESOLVED_PLAY_AS_POKEMON_RETREAT",
    "UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON",
    "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER",
    # v0.48: VS1・PG1・MH1（docs/effective-pokemon-properties-v0.48.md）。止まる場合（［へんしょく］で変えた色が、使った番のあとに読み方でダメージを変える・
    # 弱点（抵抗力）のないポケモンの色を変える・「きょだいか」の効果が消えて最大HPがのっているダメージ以下になる「にげる」・ポケモンいれかえ・かがくへんかガス）と
    # 隣の止まらない場合（使った番のうち・読み方でダメージが変わらない・弱点のあるポケモン・最大HPがダメージより大きいまま）は
    # tests/test_effective_pokemon_properties_v0_48.py の ShiftColorTest・ConversionTest・MaxHpDropTest
    "UNRESOLVED_SHIFT_COLOR_DURATION",
    "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE",
    "UNRESOLVED_MAX_HP_DROP",
    # v0.49: TE1・TF1・TF2・DG1・DG2・DG3・VA1・RC1〜RC4（docs/virtual-attacks-transformation-v0.49.md）。止まる場合と隣の止まらない場合は
    # tests/test_virtual_attacks_transformation_v0_49.py
    "UNRESOLVED_TRANSFORM_ENERGY_COUNT",
    "UNRESOLVED_TRANSFORM_COPIED_POWER",
    "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER",
    "UNRESOLVED_SHAPESHIFT_SUPPRESSED",
    "UNRESOLVED_SHAPESHIFT_ENTRY_POWER",
    "UNRESOLVED_SHAPESHIFT_AGAIN",
    "UNRESOLVED_VIRTUAL_ONCE_ATTACK",
    "UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK",
    "UNRESOLVED_RECALL_EARLIER_STAGE",
    "UNRESOLVED_RECALL_TARGET_CHANGED",
    "UNRESOLVED_RECALL_FORM",
    # v0.50: DV1・DV2・DV3・DV4・DV5（退化の途中のきぜつ・退化した番の進化・退化でもどったカードの特殊能力・自分の進化ポケモンがいない退化スプレー・「ばける」のポケモンの退化。
    # docs/mew-devolution-spray-v0.50.md）
    "UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT",
    "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION",
    "UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION",
    "UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET",
    "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED",
)
TURN = 7


def full(state):
    return state_to_dict(state, format_version=8)


class BoundaryTestCase(unittest.TestCase):
    format_version = 8  # 比べる書き出しの形式（v0.6 のあまごいの盤面は 9）

    def assert_rejected(self, state, command, code):
        """コマンドの拒否（``UnsupportedError``。状態を返さない）。渡した状態・乱数・ログは変わらない。"""
        def written(s):
            return state_to_dict(s, format_version=self.format_version)

        before, fingerprint, log = written(state), rng_fingerprint(state.rng), state.log
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, command)
        self.assertIs(type(ctx.exception), UnsupportedError)
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual((written(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertIs(state.log, log)

    def assert_halted(self, state, code):
        """対戦を止めた（``Phase.HALTED``。状態は返る）。決定は残らず、どのコマンドも同じコードで拒否する。"""
        self.assertEqual((state.phase, state.halt.code, state.decision, state.result), (Phase.HALTED, code, None, None))
        self.assertEqual(state.log[-1]["kind"], "halted")
        self.assertEqual(check_invariants(state), [])
        for player in (0, 1):
            self.assert_rejected(state, EndTurn(player), code)

    def assert_proceeds(self, state, command):
        """止まらずに処理する（どの ``UNRESOLVED_…`` でもない）。"""
        try:
            new = apply_command(state, command)
        except EngineError as error:  # pragma: no cover - 失敗の表示のため
            self.fail(f"{command} が {error.code} で止まった")
        self.assertNotEqual(new.phase, Phase.HALTED)
        self.assertEqual(check_invariants(new), [])
        return new


class MulliganCompensationTest(BoundaryTestCase):
    """p.308。両方が同時に切り直したあと、片方だけがさらに切り直した場合の補償の枚数（HALTED。new_game の中）。"""

    def test_trigger_and_neighbours(self):
        halted = new_game(FEW_BASICS, FEW_BASICS, find_seed(
            FEW_BASICS, FEW_BASICS, lambda s: s.mulligan_rounds[:1] == ((0, 1),) and len(s.mulligan_rounds[-1]) == 1))
        self.assert_halted(halted, "UNRESOLVED_MULLIGAN_COMPENSATION")
        both_only = new_game(FEW_BASICS, FEW_BASICS, find_seed(FEW_BASICS, FEW_BASICS, lambda s: s.mulligan_rounds == ((0, 1),)))
        self.assertEqual((both_only.phase, [p.mulligan_draws_remaining for p in both_only.players]), (Phase.SETUP_PLACEMENT, [0, 0]))
        single_only = new_game(FEW_BASICS, FEW_BASICS, find_seed(
            FEW_BASICS, FEW_BASICS, lambda s: s.mulligan_rounds and all(len(r) == 1 for r in s.mulligan_rounds)))
        self.assertEqual(single_only.phase, Phase.SETUP_PLACEMENT)
        self.assertGreater(sum(p.mulligan_draws_remaining for p in single_only.players), 0)


class TrainerBoundaryTest(BoundaryTestCase):
    """p.254・p.310・p.320。きずぐすり・ポケモンいれかえの、使えるか・選べるかが決められない場合（拒否）。"""

    def board(self, own_damage=0, bench_damage=None, opponent_damage=0, bench=True, hand=(POTION, SWITCH)):
        own_bench = [] if not bench else [{"card": RATTATA, "damage": bench_damage or 0}]
        return build_test_state([
            {"active": {"card": GROWLITHE, "damage": own_damage}, "bench": own_bench, "hand": list(hand)},
            {"active": {"card": RATTATA, "damage": opponent_damage}, "bench": [PONYTA]},
        ], turn_number=TURN)

    def potion(self, state):
        return PlayTrainer(0, uids(state, 0, "hand", POTION)[0])

    def test_potion_without_damage(self):
        state = self.board(opponent_damage=20)  # 相手のポケモンのダメージは関係しない（「あなたの場」）
        self.assert_rejected(state, self.potion(state), "UNRESOLVED_POTION_WITHOUT_DAMAGE")
        for state in (self.board(own_damage=10), self.board(bench_damage=10)):
            self.assertEqual(self.assert_proceeds(state, self.potion(state)).phase, Phase.DECISION)

    def test_potion_undamaged_target(self):
        state = self.assert_proceeds(self.board(own_damage=20), self.potion(self.board(own_damage=20)))
        d = state.decision
        undamaged = state.players[0].bench[0].pokemon_id
        self.assert_rejected(state, ResolveDecision(0, d.id, (undamaged,)), "UNRESOLVED_POTION_UNDAMAGED_TARGET")
        healed = self.assert_proceeds(state, ResolveDecision(0, d.id, (state.players[0].active.pokemon_id,)))
        self.assertEqual(healed.players[0].active.damage, 0)

    def test_switch_without_bench(self):
        state = self.board(bench=False)
        self.assert_rejected(state, PlayTrainer(0, uids(state, 0, "hand", SWITCH)[0]), "UNRESOLVED_SWITCH_WITHOUT_BENCH")
        state = self.board()
        self.assertEqual(self.assert_proceeds(state, PlayTrainer(0, uids(state, 0, "hand", SWITCH)[0])).phase, Phase.DECISION)

    def test_whirlwind_without_bench_is_a_different_rule(self):
        """ふきとばしの「相手に控えがいないとき、入れ替えはおこらない」（p.19）は、きまった規定なので止めない（v0.4d）。"""
        state = build_test_state([
            {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}},
            {"active": {"card": SEEL}},
        ], turn_number=TURN)
        new = self.assert_proceeds(state, UseAttack(0, 0))
        self.assertEqual([e["reason"] for e in new.log if e["kind"] == "forced_switch_skipped"], ["no_bench"])


class PokemonCheckBoundaryTest(BoundaryTestCase):
    """p.322〜p.325。ポケモンチェックのどくで両方がきぜつ・両方の対戦ポケモンがねむり（HALTED。ダメージ・コインの前）。"""

    def board(self, own, opponent, *, own_bench=(PONYTA,), opponent_bench=(PONYTA,)):
        return build_test_state([
            {"active": own, "bench": list(own_bench)},
            {"active": opponent, "bench": list(opponent_bench)},
        ], turn_number=TURN)

    def test_double_poison_knock_out(self):
        state = self.board({"card": RATTATA, "damage": 20, "poison": 10}, {"card": RATTATA, "damage": 20, "poison": 10})
        halted = apply_command(state, EndTurn(0))
        self.assert_halted(halted, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")
        self.assertEqual([p.active.damage for p in halted.players], [20, 20])  # ダメージを与える前に止めた
        self.assertNotIn("poison_damage", [e["kind"] for e in halted.log])
        self.assertEqual(rng_fingerprint(halted.rng), rng_fingerprint(state.rng))
        # 片方だけきぜつ・どちらもきぜつしない・片方だけどく は止めない
        for own, opponent in (
            ({"card": RATTATA, "damage": 10, "poison": 10}, {"card": RATTATA, "damage": 20, "poison": 10}),
            ({"card": RATTATA, "poison": 10}, {"card": RATTATA, "poison": 10}),
            ({"card": RATTATA, "damage": 20, "poison": 10}, {"card": RATTATA, "damage": 20}),
        ):
            self.assert_proceeds(self.board(own, opponent), EndTurn(0))

    def test_double_poison_knock_out_of_evolved_pokemon(self):
        """進化したポケモン（重なり 3 枚）でも同じ（v0.4c の 2 進化。きぜつの処理の前に止めるので、重なりのトラッシュもない）。"""
        evolved = {"card": BEEDRILL, "evolved_from": [WEEDLE, KAKUNA], "damage": 70, "poison": 10}
        state = self.board(evolved, {"card": RATTATA, "damage": 20, "poison": 10})
        halted = apply_command(state, EndTurn(0))
        self.assert_halted(halted, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT")
        self.assertEqual(len(halted.players[0].active.evolution_stack), 2)

    def test_both_asleep(self):
        state = self.board({"card": PARAS, "sleep": True}, {"card": PARAS, "sleep": True})
        halted = apply_command(state, EndTurn(0))
        self.assert_halted(halted, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER")
        self.assertNotIn("coin_flip", [e["kind"] for e in halted.log])
        self.assertEqual(rng_fingerprint(halted.rng), rng_fingerprint(state.rng))
        for own, opponent in (
            ({"card": PARAS, "sleep": True}, {"card": PARAS}),
            ({"card": PARAS}, {"card": PARAS, "sleep": True}),
            ({"card": PARAS, "sleep": True}, {"card": PARAS, "paralysis": TURN - 1}),
            ({"card": PARAS, "sleep": True}, {"card": PARAS, "confusion": True}),
        ):
            new = self.assert_proceeds(with_coin_results(self.board(own, opponent), T), EndTurn(0))
            self.assertEqual([e["kind"] for e in new.log].count("sleep_check"), 1)

    def test_both_asleep_after_poison_knock_out_is_not_reached(self):
        """2 のどくで片方がきぜつしたら、そのポケモンのねむりのコインは投げない（3 の前にきぜつ・交代。v0.3b）。両方ねむりでも、
        片方がどくできぜつするなら止めない。"""
        state = self.board({"card": PARAS, "sleep": True, "poison": 10, "damage": 30}, {"card": PARAS, "sleep": True})
        new = self.assert_proceeds(state, EndTurn(0))
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))


class ParalysisBoundaryTest(BoundaryTestCase):
    """p.322・p.323。マヒの再付与で回復する番が変わる場合。今の対応カード（相手の対戦ポケモンだけをマヒにする）では起こらない
    ので、確認の関数を直接呼ぶ。ワザ（いとをはく・しびれごな・れいとうビーム）での再付与は回復する番が同じなので止めない。"""

    def test_trigger_by_direct_call(self):
        state = build_test_state([{"active": {"card": GROWLITHE, "paralysis": TURN - 1}}, {"active": RATTATA}], turn_number=TURN)
        self.assertEqual(paralysis_problem(state, 0, state.players[0].active).code, "UNRESOLVED_REPARALYSIS_RECOVERY_TURN")
        self.assertIsNone(paralysis_problem(state, 1, state.players[1].active))

    def test_reparalysis_by_attacks_proceeds(self):
        for attacker, index, energy in ((CATERPIE, 0, [GRASS]), (METAPOD, 1, [GRASS, GRASS]), (DEWGONG, 1, [WATER] * 4)):
            below = {CATERPIE: None, METAPOD: CATERPIE, DEWGONG: SEEL}[attacker]
            spec = {"card": attacker, "energy": energy, **({"evolved_from": below} if below else {})}
            with self.subTest(attacker=attacker):
                state = build_test_state([
                    {"active": spec}, {"active": {"card": SEEL, "paralysis": TURN - 1}, "bench": [PONYTA]},
                ], turn_number=TURN)
                new = self.assert_proceeds(with_coin_results(state, H), UseAttack(0, index))
                applied = next(e for e in new.log if e["kind"] == "special_condition")
                self.assertTrue(applied["already"])


class ConfusionBoundaryTest(BoundaryTestCase):
    """p.257・p.309・p.321・p.322。こんらんしたワザの 20 にプラスパワー・ディフェンダーを計算するか（拒否。こんらんのコインの前）。
    にげるの失敗のあとこんらんが消えたポケモンの再宣言（p.311。拒否。エネルギーのトラッシュの前）。"""

    def board(self, attacker, *, bench=({"card": PONYTA},), opponent=None):
        return build_test_state([
            {"active": attacker, "bench": list(bench), "hand": [SWITCH, SWITCH]},
            {"active": opponent or {"card": RATTATA}, "bench": [PONYTA]},
        ], turn_number=TURN)

    def test_confusion_damage_modifiers(self):
        vulpix = {"card": VULPIX, "energy": [FIRE, FIRE], "confusion": True}
        for trainers in ([(PLUSPOWER, TURN)], [(DEFENDER, TURN + 1)], [(PLUSPOWER, TURN), (DEFENDER, TURN + 1)]):
            with self.subTest(trainers=trainers):
                self.assert_rejected(self.board({**vulpix, "trainers": trainers}), UseAttack(0, 0), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")
        # 進化したポケモン（バタフリー）でも同じ。メガドレインのワザでも、こんらんのコインの前に止める
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4, "confusion": True,
                      "trainers": [(PLUSPOWER, TURN)]}
        self.assert_rejected(self.board(butterfree), UseAttack(0, 1), "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS")
        # 止めない: こんらんでない・ついていない・ベンチのポケモンについている・相手についている
        neighbours = (
            ({**vulpix, "confusion": False, "trainers": [(PLUSPOWER, TURN)]}, ({"card": PONYTA},), None),
            (vulpix, ({"card": PONYTA},), None),
            (vulpix, ({"card": PONYTA, "trainers": [(DEFENDER, TURN + 1)]},), None),
            (vulpix, ({"card": PONYTA},), {"card": RATTATA, "trainers": [(DEFENDER, TURN)]}),
        )
        for attacker, bench, opponent in neighbours:
            attacker = {k: v for k, v in attacker.items() if not (k == "confusion" and v is False)}
            self.assert_proceeds(with_coin_results(self.board(attacker, bench=bench, opponent=opponent), T, T), UseAttack(0, 0))

    def test_retreat_after_confusion_cleared(self):
        """こんらんで失敗 →「ポケモンいれかえ」でベンチへ（こんらんが消える）→ もう一度「ポケモンいれかえ」でバトル場へ →「にげる」。
        自然な対戦で起こる流れ。"""
        state = self.board({"card": VULPIX, "energy": [FIRE, FIRE], "confusion": True})
        vulpix = state.players[0].active
        failed = apply_command(with_coin_results(state, T), Retreat(0, (vulpix.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(failed.players[0].active.retreat_failed_turn, TURN)
        # こんらんのまま: 決められる（RETREAT_ALREADY_FAILED。拒否だが UNRESOLVED ではない）
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(failed, Retreat(0, (failed.players[0].active.energy[0],), failed.players[0].bench[0].card))
        self.assertEqual(ctx.exception.code, "RETREAT_ALREADY_FAILED")
        switched = failed
        for _ in range(2):
            switched = apply_command(switched, PlayTrainer(0, uids(switched, 0, "hand", SWITCH)[0]))
            switched = apply_command(switched, ResolveDecision(0, switched.decision.id, (switched.decision.options[0],)))
        back = switched.players[0].active
        self.assertEqual((back.pokemon_id, back.conditions.names(), back.retreat_failed_turn), (vulpix.pokemon_id, (), TURN))
        self.assert_rejected(switched, Retreat(0, (back.energy[0],), switched.players[0].bench[0].card),
                             "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED")
        # 次の自分の番には記録が消えている（p.311）
        later = apply_command(apply_command(switched, EndTurn(0)), EndTurn(1))
        self.assertIsNone(later.players[0].active.retreat_failed_turn)
        self.assert_proceeds(later, Retreat(0, (later.players[0].active.energy[0],), later.players[0].bench[0].card))


class EvolutionHpBoundaryTest(BoundaryTestCase):
    """p.310・p.323。進化したあとの HP がのっているダメージ以下になる場合（拒否）。今の対応カードでは起こらない（HP は増えるか、
    コクーン → スピアーで同じ 80）ので、HP を下げたテスト専用のパラセクトで確かめる。"""

    def test_trigger_and_neighbours(self):
        def low_hp(record):
            record["pokemon"]["hp"] = 30
        pool, effects = test_pool(("TEST-LOW-HP-PARASECT", low_hp))
        for damage, stopped in ((30, True), (20, False)):
            state = build_test_state([
                {"active": {"card": PARAS, "damage": damage}, "hand": ["TEST-LOW-HP-PARASECT"]}, {"active": RATTATA},
            ], turn_number=TURN, pool=pool, effects=effects)
            command = EvolvePokemon(0, uids(state, 0, "hand", "TEST-LOW-HP-PARASECT")[0], state.players[0].active.pokemon_id)
            if stopped:
                self.assert_rejected(state, command, "UNRESOLVED_EVOLUTION_HP")
            else:
                self.assert_proceeds(state, command)
        # 実在のカードで HP が同じ（コクーン 80 → スピアー 80）: のっているダメージは HP 未満なので止めない
        state = build_test_state([
            {"active": {"card": KAKUNA, "evolved_from": WEEDLE, "damage": 70}, "hand": [BEEDRILL]}, {"active": RATTATA},
        ], turn_number=TURN)
        self.assert_proceeds(state, EvolvePokemon(0, uids(state, 0, "hand", BEEDRILL)[0], state.players[0].active.pokemon_id))


class PreventedCoinDamageBoundaryTest(BoundaryTestCase):
    """p.309・p.319〜p.321。「ダメージを受けない」相手に、コインでダメージの量を決めるワザ（拒否。こんらんのコインの前）。"""

    def board(self, attacker, *, prevent=True):
        target = {"card": METAPOD, "evolved_from": CATERPIE, "energy": [GRASS], **({"prevent_damage": TURN - 1} if prevent else {})}
        return build_test_state([{"active": attacker, "bench": [RATTATA]}, {"active": target, "bench": [PONYTA]}], turn_number=TURN)

    def test_trigger_and_neighbours(self):
        doduo = {"card": DODUO, "energy": [FIRE]}
        beedrill = {"card": BEEDRILL, "evolved_from": [WEEDLE, KAKUNA], "energy": [GRASS] * 3}
        for attacker in (doduo, beedrill, {**doduo, "confusion": True}):
            with self.subTest(attacker=attacker["card"], confused=attacker.get("confusion", False)):
                self.assert_rejected(self.board(attacker), UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        # 止めない: ダメージを受けない状態でない相手・ダメージ以外の効果のあるワザ（どくばり）・ふきとばし
        self.assert_proceeds(with_coin_results(self.board(doduo, prevent=False), H, T), UseAttack(0, 0))
        poisoned = self.assert_proceeds(with_coin_results(self.board(beedrill), H), UseAttack(0, 1))
        self.assertIn("damage_prevented", [e["kind"] for e in poisoned.log])
        self.assertIsNotNone(poisoned.players[1].active.conditions.poison)
        whirlwind = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        self.assertEqual(self.assert_proceeds(self.board(whirlwind), UseAttack(0, 0)).phase, Phase.DECISION)


class AttachAfterPowerAttachBoundaryTest(BoundaryTestCase):
    """p.310「ポケモンにつけることのできるエネルギーカードの数は、1回の自分の番ごとに1枚だけです」・p.307（カードの記述を優先）・
    p.90（カメックスの「あまごい」の最新の説明）。v0.6（docs/rain-dance-v0.6.md の R11〜R13）。

    止まる場合: この番に「あまごい」で手札からエネルギーをつけていて、手札からつける通常の操作をまだしていない番の、通常の操作
    （拒否。カードを動かす前）。あまごいでつけたカードを p.310 の「1枚」に数えるかが原典に書かれていないので、受け付けるとも
    拒否する（ENERGY_ALREADY_ATTACHED）とも決めない。ここでは「止まること・状態が変わらないこと」だけを確かめる（裁定を
    テストで決めない）。

    隣の止まらない場合: 通常の操作のあとのあまごい（R12。どちらの読み方でも使える）・エナジートランス（場のエネルギーのつけかえ。
    手札からつけない）のあとの通常の操作・前の自分の番にあまごいを使った番の通常の操作（番の最初に数を 0 にする）・拒否された
    あまごい（状態を変えない）のあとの通常の操作。"""

    format_version = 9

    def board(self, *, active=None, bench=(), hand=(WATER, WATER, FIRE), attached=0):
        blastoise = {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE]}
        return build_test_state([
            {"active": active or blastoise, "bench": list(bench) or [RATTATA], "hand": list(hand)}, {"active": GROWLITHE},
        ], turn_number=TURN, energy_attachments_this_turn=attached)

    def rain_dance(self, state, energy, target=None):
        me = state.players[0]
        user = next(pk for pk in me.in_play() if state.cards[pk.card].card_id == BLASTOISE)
        return UsePokemonPower(0, user.pokemon_id, 0, energy, None, (target or me.active).pokemon_id)

    def test_trigger_and_neighbours(self):
        state = self.board()
        waters = uids(state, 0, "hand", WATER)
        fire = uids(state, 0, "hand", FIRE)[0]
        once = self.assert_proceeds(state, self.rain_dance(state, waters[0]))
        twice = self.assert_proceeds(once, self.rain_dance(once, waters[1]))
        rattata = state.players[0].bench[0].card
        for powered in (once, twice):
            for command in (AttachEnergy(0, fire, powered.players[0].active.card), AttachEnergy(0, fire, rattata)):
                with self.subTest(uses=powered.energy_attached_by_powers_this_turn, target=command.target):
                    self.assert_rejected(powered, command, "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH")
        self.assert_rejected(once, AttachEnergy(0, waters[1], once.players[0].active.card), "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH")
        # ほかの理由で正しくない通常の操作は、その理由で拒否する（手札にない・相手のポケモン）。止めるのは、ほかの確認が通ったときだけ
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(once, AttachEnergy(0, waters[0], rattata))
        self.assertEqual(ctx.exception.code, "CARD_NOT_IN_HAND")
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(once, AttachEnergy(0, fire, once.players[1].active.card))
        self.assertEqual(ctx.exception.code, "TARGET_NOT_YOURS")

        # 止めない 1: 通常の操作のあとのあまごい（R12）。そのあとの 2 回目の通常の操作は、1 番に 1 枚の規定で拒否（ENERGY_ALREADY_ATTACHED）
        attached = self.assert_proceeds(state, AttachEnergy(0, fire, rattata))
        powered = self.assert_proceeds(attached, self.rain_dance(attached, waters[0]))
        self.assertEqual((powered.energy_attachments_this_turn, powered.energy_attached_by_powers_this_turn), (1, 1))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(powered, AttachEnergy(0, waters[1], rattata))
        self.assertEqual(ctx.exception.code, "ENERGY_ALREADY_ATTACHED")
        # 止めない 2: 前の自分の番にあまごいを使っても、次の自分の番の通常の操作は止めない（番の最初に 0）
        later = self.assert_proceeds(once, EndTurn(0))
        later = self.assert_proceeds(later, EndTurn(1))
        self.assertEqual((later.current_player, later.energy_attached_by_powers_this_turn), (0, 0))
        self.assert_proceeds(later, AttachEnergy(0, fire, later.players[0].active.card))
        # 止めない 3: 拒否されたあまごい（相手のポケモンへ）のあとの通常の操作
        with self.assertRaises(IllegalActionError):
            apply_command(state, self.rain_dance(state, waters[0], state.players[1].active))
        self.assert_proceeds(state, AttachEnergy(0, fire, rattata))
        # 止めない 4: エナジートランス（場のエネルギーのつけかえ。手札からつけない）のあとの通常の操作
        venusaur = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], "energy": [GRASS, GRASS]}
        trans = build_test_state([{"active": venusaur, "bench": [BULBASAUR], "hand": [GRASS]}, {"active": GROWLITHE}], turn_number=TURN)
        me = trans.players[0]
        moved = self.assert_proceeds(trans, UsePokemonPower(0, me.active.pokemon_id, 0, me.active.energy[0], me.active.pokemon_id,
                                                            me.bench[0].pokemon_id))
        self.assertEqual(moved.energy_attached_by_powers_this_turn, 0)
        self.assert_proceeds(moved, AttachEnergy(0, uids(moved, 0, "hand", GRASS)[0], me.active.card))


class EvadedEffectCoinBoundaryTest(BoundaryTestCase):
    """p.160（ゴーストの「とうめい」の最新の説明）・p.159（特殊能力解説）・p.309・p.321。v0.9（docs/transparency-v0.9.md の T19b）。

    止まる場合: 相手の対戦ポケモンの「とうめい」がはたらいていて、「ダメージ → ワザを使う側のコイン → 相手を特殊状態にする」ワザの
    ダメージの要素の最終ダメージが 0 より大きい（受ける要素で「とうめい」のコインを投げうる）とき。「おもて」なら、そのあとのワザの
    コインが「受けない」ポケモンへの効果だけを決めるが、それを投げるかが原典に書かれていない。拒否はこんらんのコインの前（ワザを
    使うポケモンがこんらんでも同じ。コインの結果で受け付けるかが変わらない）。

    隣の止まらない場合: ゴーストがねむり（力が消える。T9）・かがくへんかガスがはたらいている（T14）・相手の対戦ポケモンが
    「とうめい」を持たない（ゴース）・ゴーストがベンチ（ワザの要素はバトル場のポケモンにだけ）・最終ダメージが 0（ディフェンダー。
    T21。ワザのコインのあとで「とうめい」のコイン）・コインを使わずに特殊状態にするワザ（「あくむ」。T4 の 1 回のコインで決まる）。"""

    format_version = 9

    def board(self, attacker, *, defender=None, bench=(), mine_bench=()):
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        return build_test_state([
            {"active": attacker, "bench": list(mine_bench) or [RATTATA]},
            {"active": defender or haunter, "bench": list(bench) or [PONYTA]},
        ], turn_number=TURN)

    def test_trigger_and_neighbours(self):
        weedle = {"card": WEEDLE, "energy": [GRASS]}
        gastly = {"card": GASTLY, "energy": [PSYCHIC]}
        vulpix = {"card": VULPIX, "energy": [FIRE, FIRE]}
        caterpie = {"card": CATERPIE, "energy": [GRASS]}
        attackers = ((weedle, 0), (gastly, 0), (vulpix, 0), (caterpie, 0), ({**weedle, "confusion": True}, 0))
        for attacker, index in attackers:
            with self.subTest(attacker=attacker["card"], confused=attacker.get("confusion", False)):
                self.assert_rejected(self.board(attacker), UseAttack(0, index), "UNRESOLVED_EVADED_EFFECT_COIN")
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        # 止めない 1: ねむりのゴースト（「とうめい」の力が消えている。T9）。ワザのコインだけ
        asleep = self.assert_proceeds(with_coin_results(self.board(weedle, defender={**haunter, "sleep": True}), H), UseAttack(0, 0))
        self.assertNotIn("evade_check", [e["kind"] for e in asleep.log])
        self.assertIsNotNone(asleep.players[1].active.conditions.poison)
        # 止めない 2: かがくへんかガス（場のどこかのベトベトン。T14）
        muk = {"card": MUK, "evolved_from": GRIMER}
        gassed = self.assert_proceeds(with_coin_results(self.board(weedle, mine_bench=[muk]), T), UseAttack(0, 0))
        self.assertNotIn("evade_check", [e["kind"] for e in gassed.log])
        # 止めない 3: 相手の対戦ポケモンが「とうめい」を持たない（ゴース）。ベンチのゴーストはワザを受けない
        plain = self.assert_proceeds(with_coin_results(self.board(weedle, defender=GASTLY, bench=[haunter]), T), UseAttack(0, 0))
        self.assertNotIn("evade_check", [e["kind"] for e in plain.log])
        # 止めない 4: 最終ダメージが 0（ディフェンダーで 10 - 20）。ワザのコイン（「おもて」）→ どくを受けるときに「とうめい」のコイン
        defended = {**haunter, "trainers": [(DEFENDER, TURN)]}
        late = self.assert_proceeds(with_coin_results(self.board(weedle, defender=defended), H, T), UseAttack(0, 0))
        coins = [e for e in late.log if e["kind"] == "coin_flip"]
        self.assertEqual([c["source"] for c in coins[-2:]], ["attack", "power"])
        self.assertIsNotNone(late.players[1].active.conditions.poison)
        # 止めない 5: コインを使わずにねむりにする「あくむ」（受ける要素で 1 回だけ投げ、結果をねむりにも使う。T4）
        nightmare = {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        evaded = self.assert_proceeds(with_coin_results(self.board(nightmare), H), UseAttack(0, 0))
        self.assertEqual([e["element"] for e in evaded.log if e["kind"] == "attack_evaded"], ["damage", "sleep"])


class RecoverZeroEnergyBoundaryTest(BoundaryTestCase):
    """p.158（化石の秘密のゴースの「エナジーへんかん」の最新の説明「自分のトラッシュから、「エネルギーカード」を最大2枚選び出し、
    手札に加える。その後、自分に10ダメージ。」）。v0.9（docs/haunter-line-v0.9.md の H4）。

    止まる場合: トラッシュにエネルギーカードがあるのに 0 枚を選ぶ（決定に答える ``ResolveDecision`` の拒否。決定は待ったまま）。
    「最大2枚」が 0 枚を含むかが書かれていないので、受け付けるとも拒否する（INVALID_CHOICE_COUNT）とも決めない。

    隣の止まらない場合: 1 枚・2 枚を選ぶ・トラッシュにエネルギーカードがない（決定を出さずに自分へのダメージだけ。H5）。"""

    format_version = 9

    def board(self, discard):
        gastly = {"card": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        return build_test_state([{"active": gastly, "bench": [RATTATA], "discard": list(discard)}, {"active": GROWLITHE}],
                                turn_number=TURN)

    def test_trigger_and_neighbours(self):
        state = self.assert_proceeds(self.board([FIRE, PSYCHIC, POTION, WATER]), UseAttack(0, 1))
        self.assertEqual((state.phase, state.decision.min_choices, state.decision.max_choices), (Phase.DECISION, 0, 2))
        decision = state.decision.id
        self.assert_rejected(state, ResolveDecision(0, decision, ()), "UNRESOLVED_RECOVER_ZERO_ENERGY")
        energies = state.decision.options
        self.assertEqual(len(energies), 3)
        for choices in ((energies[0],), energies[1:]):
            with self.subTest(choices=choices):
                done = self.assert_proceeds(state, ResolveDecision(0, decision, choices))
                self.assertTrue(set(choices) <= set(done.players[0].hand))
                self.assertEqual(done.players[0].active.damage, 10)
        empty = self.assert_proceeds(self.board([POTION]), UseAttack(0, 1))
        self.assertIsNone(empty.decision)
        self.assertEqual(empty.players[0].active.damage, 10)


class CounterattackDoubleKnockoutBoundaryTest(BoundaryTestCase):
    """p.192（カイリキーの「はんげき」の最新の説明「（それによってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、…10ダメージ」）・
    p.324（「1つのワザや特殊能力などによって引き起こされることがらによって複数のポケモンが「きぜつ」した場合、…同時に」）。v0.10
    （docs/counterattack-v0.10.md の C18）。

    止まる場合（ワザの宣言の前の拒否。こんらんのコインの前）: ワザのダメージで「はんげき」がはたらいているカイリキーがきぜつし、かつ「はんげき」
    の 10 でワザを使ったポケモンがきぜつする（コインのどれかの結果でそうなりうる）。ワザによるきぜつと特殊能力によるきぜつが同時かが
    決められない（サイド・バトル場に出す順番と勝ち負けが変わる）。

    隣の止まらない場合: カイリキーがねむり（はたらかない。C19）・かがくへんかガス（C24）・カイリキーがきぜつしない（「はんげき」だけで
    ワザを使ったポケモンがきぜつする 1 匹のきぜつ）・ワザを使ったポケモンが「はんげき」のあとも HP 未満・ワザを使ったポケモンが自分への
    ダメージですでにきぜつ（「はんげき」は与えない。1 つのワザによる同時のきぜつ。C15）・ディフェンダーでカイリキーがきぜつしない。"""

    format_version = 9

    def board(self, attacker, *, machamp=None, mine_bench=()):
        champ = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], **(machamp or {})}
        return build_test_state([
            {"active": attacker, "bench": list(mine_bench) or [RATTATA]},
            {"active": champ, "bench": [PONYTA]},
        ], turn_number=TURN)

    def test_trigger_and_neighbours(self):
        hitmonchan = {"card": HITMONCHAN, "damage": 60, "energy": [FIGHTING] * 3}  # HP 70。スペシャルパンチ 40
        pikachu = {"card": PIKACHU, "damage": 30, "energy": [LIGHTNING] * 3}  # HP 40。でんげき 30（「うら」なら自分にも 10）
        triggers = (
            (hitmonchan, 1, {"damage": 80}),
            ({**hitmonchan, "confusion": True}, 1, {"damage": 80}),  # こんらんのコインの前に止める
            (pikachu, 1, {"damage": 70}),  # 「おもて」なら自分へのダメージがなく「はんげき」できぜつ（「うら」なら自分へのダメージできぜつ）
            ({"card": MACHOKE, "evolved_from": MACHOP, "damage": 50, "energy": [FIGHTING] * 4}, 1, {"damage": 40}),  # じごくぐるま 60・自分に 20
        )
        for attacker, index, machamp in triggers:
            with self.subTest(attacker=attacker["card"], confused=attacker.get("confusion", False)):
                self.assert_rejected(self.board(attacker, machamp=machamp), UseAttack(0, index), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        # 止めない 1: ねむりのカイリキー（「はんげき」ははたらかない）。カイリキーだけがきぜつする
        asleep = self.assert_proceeds(self.board(hitmonchan, machamp={"damage": 80, "sleep": True}), UseAttack(0, 1))
        self.assertNotIn("counterattack", [e["kind"] for e in asleep.log])
        # 止めない 2: かがくへんかガス（自分の場のベトベトン）
        gassed = self.assert_proceeds(self.board(hitmonchan, machamp={"damage": 80}, mine_bench=[{"card": MUK, "evolved_from": GRIMER}]),
                                      UseAttack(0, 1))
        self.assertNotIn("counterattack", [e["kind"] for e in gassed.log])
        # 止めない 3: カイリキーはきぜつしない（ワザを使ったポケモンだけが「はんげき」できぜつする。1 匹のきぜつ）
        single = self.assert_proceeds(self.board(hitmonchan, machamp={"damage": 50}), UseAttack(0, 1))
        self.assertEqual([(e["kind"], e["player"]) for e in single.log if e["kind"] == "knock_out"], [("knock_out", 0)])
        # 止めない 4: ワザを使ったポケモンは「はんげき」のあとも HP 未満（カイリキーだけがきぜつする）
        survivor = self.assert_proceeds(self.board({**hitmonchan, "damage": 50}, machamp={"damage": 80}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in survivor.log if e["kind"] == "knock_out"], [1])
        self.assertEqual(survivor.players[0].active.damage, 60)
        # 止めない 5: じごくぐるまの自分への 20 ですでにきぜつ（「はんげき」は与えない。1 つのワザによる同時のきぜつ。p.324）
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "damage": 60, "energy": [FIGHTING] * 4}
        both = self.assert_proceeds(self.board(machoke, machamp={"damage": 40}), UseAttack(0, 1))
        self.assertIn("counterattack_skipped", [e["kind"] for e in both.log])
        self.assertEqual([e.get("simultaneous") for e in both.log if e["kind"] == "knock_out"], [True, True])
        # 止めない 6: ディフェンダーで 40 - 20 = 20（カイリキーはきぜつしない。「はんげき」でワザを使ったポケモンがきぜつ）
        defended = self.assert_proceeds(self.board(hitmonchan, machamp={"damage": 70, "trainers": [(DEFENDER, TURN)]}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in defended.log if e["kind"] == "knock_out"], [0])
        # 止めない 7: 最終ダメージが 0（ディグダのあなをほる 10 - ディフェンダー 20）。「はんげき」ははたらかない
        zero = self.assert_proceeds(self.board({"card": DIGLETT, "damage": 30, "energy": [FIGHTING]}, machamp={"damage": 90, "trainers": [(DEFENDER, TURN)]}),
                                    UseAttack(0, 0))
        self.assertNotIn("counterattack", [e["kind"] for e in zero.log])


class KoPreventionAttackEffectTest(BoundaryTestCase):
    """p.193（サカキのカイリキーの「こんじょう」の最新の説明・解説）・p.89・p.213（ダメージできぜつしなければあとの効果）・p.309・p.311・
    p.320〜p.324。v0.11（docs/guts-v0.11.md の G30・G37）。

    止まる場合（ワザの宣言の前の拒否。こんらんのコインの前）: 相手の対戦ポケモンのサカキのカイリキーが「こんじょう」を使える（ねむり・マヒ・
    こんらんでなく、かがくへんかガスがない）とき、そのワザのダメージのどれかの候補で HP 以上になり、同じワザで相手の対戦ポケモンに効果
    （特殊状態・入れ替え）を与える。「おもて」で「きぜつ」しなかったポケモンがその効果を受けるかが決められない。

    隣の止まらない場合: HP 以上にならない・「こんじょう」を使えない（ねむり・かがくへんかガス）・ディフェンダーで最終ダメージが 0・ダメージの
    要素のないワザ（キノコのほうし・どくガス）・相手に効果を与えないワザ（決定を出す）。"""

    format_version = 9

    def board(self, attacker, *, machamp=None, mine_bench=()):
        champ = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], **(machamp or {})}
        return build_test_state([
            {"active": attacker, "bench": list(mine_bench) or [RATTATA]},
            {"active": champ, "bench": [PONYTA]},
        ], turn_number=TURN)

    def test_trigger_and_neighbours(self):
        caterpie = {"card": CATERPIE, "energy": [GRASS]}  # いとをはく 10（「おもて」ならマヒ）
        triggers = (
            (caterpie, 0, {"damage": 90}),
            ({**caterpie, "confusion": True}, 0, {"damage": 90}),  # こんらんのコインの前に止める
            ({"card": WEEDLE, "energy": [GRASS]}, 0, {"damage": 90}),  # どくばり 10（「おもて」ならどく）
            ({"card": IVYSAUR, "evolved_from": BULBASAUR, "energy": [GRASS] * 3}, 1, {"damage": 80}),  # どくのこな 20（どく。コインなし）
            ({"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC] * 2}, 0, {"damage": 80}),  # あくむ 10 × 弱点 2（ねむり）
            ({"card": VULPIX, "energy": [FIRE] * 2}, 0, {"damage": 90}),  # あやしいひかり 10（「おもて」ならこんらん）
            ({"card": GIOVANNIS_MACHOKE, "evolved_from": GIOVANNIS_MACHOP, "energy": [FIGHTING] * 3}, 1, {"damage": 60}),  # じごくがため（「おもて」40）
            ({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 2}, 0, {"damage": 80}),  # ふきとばし 20（入れ替え）
            ({"card": GRIMER, "energy": [GRASS] * 2}, 1, {"damage": 70}),  # ねばりつく（「おもて」30）
        )
        for attacker, index, machamp in triggers:
            with self.subTest(attacker=attacker["card"], confused=attacker.get("confusion", False)):
                self.assert_rejected(self.board(attacker, machamp=machamp), UseAttack(0, index), "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")
        # 止めない 1: HP 以上にならない（80 + 10）。いつもどおり効果を与える
        alive = self.assert_proceeds(with_coin_results(self.board(caterpie, machamp={"damage": 80}), H), UseAttack(0, 0))
        self.assertTrue(alive.players[1].active.conditions.paralyzed)
        # 止めない 2: ねむりのサカキのカイリキー（「こんじょう」を使えない）。きぜつして効果は与えない（v0.4d）
        asleep = self.assert_proceeds(with_coin_results(self.board(caterpie, machamp={"damage": 90, "sleep": True}), H), UseAttack(0, 0))
        self.assertEqual((asleep.decision.kind, asleep.players[1].active), ("take_prize", None))
        # 止めない 3: かがくへんかガス（自分の場のベトベトン）
        gassed = self.assert_proceeds(self.board(caterpie, machamp={"damage": 90}, mine_bench=[{"card": MUK, "evolved_from": GRIMER}]),
                                      UseAttack(0, 0))
        self.assertEqual(gassed.decision.kind, "take_prize")
        # 止めない 4: ディフェンダーで 10 − 20 = 0（HP 以上にならない）
        self.assert_proceeds(self.board(caterpie, machamp={"damage": 90, "trainers": [(DEFENDER, TURN)]}), UseAttack(0, 0))
        # 止めない 5: ダメージの要素のないワザ（パラスのキノコのほうし・ロケット団のベトベターのどくガス）
        self.assert_proceeds(self.board({"card": PARAS, "energy": [GRASS] * 2}, machamp={"damage": 90}), UseAttack(0, 1))
        self.assert_proceeds(self.board({"card": GRIMER, "energy": [GRASS]}, machamp={"damage": 90}), UseAttack(0, 0))
        # 止めない 6: 相手に効果を与えないワザ（スペシャルパンチ 40）。「こんじょう」を使うかの決定を出す
        offered = self.assert_proceeds(self.board({"card": HITMONCHAN, "energy": [FIGHTING] * 3}, machamp={"damage": 80}), UseAttack(0, 1))
        self.assertEqual(offered.decision.kind, "ko_prevention")


class RetaliationDoubleKnockoutBoundaryTest(BoundaryTestCase):
    """p.82（R団のファイヤーの「ほのおのかべ」の最新の説明「次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによって
    このカードが「きぜつ」しても、）相手に10ダメージを与える。」）・p.89（同じ「相手の番ではたらく効果」の「こうらがえし」のワザ解説）・p.321「8」・
    p.324（「1つのワザや特殊能力などによって引き起こされることがらによって複数のポケモンが「きぜつ」した場合、…同時に」）。v0.12
    （docs/rocket-moltres-v0.12.md の W24）。

    止まる場合（ワザの宣言の前の拒否。こんらんのコインの前）: 相手の対戦ポケモン（R団のファイヤー）に今の番にはたらく「ほのおのかべ」があり、
    このワザのダメージ（と、「ほのおのかべ」のダメージではたらくワザを使ったポケモンの「はんげき」）で R団のファイヤーがきぜつし、かつ
    「ほのおのかべ」のダメージでワザを使ったポケモンがきぜつする（コインのどれかの結果でそうなりうる。「とうめい」は受けるほうを仮定）。
    このワザによるきぜつと、前の番のワザの効果のダメージによるきぜつが同時かが決められない。かがくへんかガス・R団のファイヤーの特殊状態
    では止めをはずさない（ワザの効果。W7・W18）。

    隣の止まらない場合: 効果がない（期限・まだ与えていない）・R団のファイヤーがきぜつしない（ワザを使ったポケモンだけが「ほのおのかべ」で
    きぜつする）・ワザを使ったポケモンが「ほのおのかべ」のあとも HP 未満・ワザを使ったポケモンが自分へのダメージですでにきぜつ（「ほのおの
    かべ」は与えない。1 つのワザによる同時のきぜつ。W23）・ディフェンダーで「ほのおのかべ」のダメージが 0。"""

    format_version = 9

    def board(self, attacker, *, moltres=None, mine_bench=(), effect=True):
        holder = {"card": ROCKETS_MOLTRES, **({"retaliation": TURN - 1} if effect else {}), **(moltres or {})}
        return build_test_state([
            {"active": attacker, "bench": list(mine_bench) or [RATTATA]},
            {"active": holder, "bench": [PONYTA]},
        ], turn_number=TURN)

    def test_trigger_and_neighbours(self):
        code = "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"
        hitmonchan = {"card": HITMONCHAN, "damage": 60, "energy": [FIGHTING] * 3}  # HP 70。スペシャルパンチ 40（抵抗力 闘 −30 で 10）
        pikachu = {"card": PIKACHU, "damage": 30, "energy": [LIGHTNING] * 3}  # HP 40。でんげき 30（「うら」なら自分にも 10）
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 90, "energy": [FIGHTING] * 4}  # ちきゅうなげ 60 → 30
        triggers = (
            (hitmonchan, 1, {"damage": 50}, ()),
            ({**hitmonchan, "confusion": True}, 1, {"damage": 50}, ()),  # こんらんのコインの前に止める
            (pikachu, 1, {"damage": 30}, ()),  # 「おもて」なら自分へのダメージがなく「ほのおのかべ」できぜつ（「うら」なら自分へのダメージ）
            (machamp, 0, {"damage": 20}, ()),  # 30 で 50、「はんげき」の 10 で 60（R団のファイヤーのきぜつは「はんげき」）
            (hitmonchan, 1, {"damage": 50, "sleep": True}, ()),  # ねむりの R団のファイヤーでも効果ははたらく（W7）
            (hitmonchan, 1, {"damage": 50}, [{"card": MUK, "evolved_from": GRIMER}]),  # かがくへんかガスでも（W18）
        )
        for attacker, index, moltres, bench in triggers:
            with self.subTest(attacker=attacker["card"], moltres=moltres, gas=bool(bench), confused=attacker.get("confusion", False)):
                self.assert_rejected(self.board(attacker, moltres=moltres, mine_bench=bench), UseAttack(0, index), code)
        # 止めない 1: 効果がない（R団のファイヤーだけがきぜつする）
        plain = self.assert_proceeds(self.board(hitmonchan, moltres={"damage": 50}, effect=False), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in plain.log if e["kind"] == "knock_out"], [1])
        # 止めない 2: R団のファイヤーはきぜつしない（ワザを使ったポケモンだけが「ほのおのかべ」できぜつする）
        single = self.assert_proceeds(self.board(hitmonchan, moltres={"damage": 0}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in single.log if e["kind"] == "knock_out"], [0])
        # 止めない 3: ワザを使ったポケモンは「ほのおのかべ」のあとも HP 未満（R団のファイヤーだけがきぜつする）
        survivor = self.assert_proceeds(self.board({**hitmonchan, "damage": 50}, moltres={"damage": 50}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in survivor.log if e["kind"] == "knock_out"], [1])
        self.assertEqual(survivor.players[0].active.damage, 60)
        # 止めない 4: じごくぐるまの自分への 20 ですでにきぜつ（「ほのおのかべ」は与えない。1 つのワザによる同時のきぜつ。p.324・W23）
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "damage": 60, "energy": [FIGHTING] * 4}
        both = self.assert_proceeds(self.board(machoke, moltres={"damage": 30}), UseAttack(0, 1))
        self.assertIn("retaliation_skipped", [e["kind"] for e in both.log])
        self.assertEqual([e.get("simultaneous") for e in both.log if e["kind"] == "knock_out"], [True, True])
        # 止めない 5: ディフェンダーで「ほのおのかべ」の 10 - 20 = 0（ワザを使ったポケモンはきぜつしない。R団のファイヤーだけがきぜつ）
        defended = self.assert_proceeds(self.board({**hitmonchan, "trainers": [(DEFENDER, TURN + 1)]}, moltres={"damage": 50}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in defended.log if e["kind"] == "knock_out"], [1])


class EffectAfterNoDamageBoundaryTest(BoundaryTestCase):
    """p.245（R団のカビゴンの「たおれこむ」の最新の説明「ダメージを与えた後、自分を「ねむり」状態にする。」）・p.155（ナツメのヤドンの同じ文面の
    解説「相手にダメージを与えたら、自分がねむり状態になってしまいます」）・p.320（ワザの要素の順番）・p.321（「ダメージを受けない」状態でも
    ダメージ以外の効果の要素は有効。最終ダメージが 0 なら「ダメージを与えなかった」）。v0.17b（docs/rocket-snorlax-v0.17b.md の Z23）。

    止まる場合（ワザの宣言の前。こんらんのコインの前）: たおれこむのダメージが、どれかのコインの結果で、相手にダメージを与えない（ディフェンダーで
    0・「ダメージを受けない」状態・「とうめい」で受けない）。「ダメージを与えた後」が順番か条件かが決められない。

    隣の止まらない場合: プラスパワーで 30 − 20 = 10 を与える・相手をきぜつさせる（ダメージを与えた）。"""

    format_version = 9

    def board(self, attacker=None, defender=None):
        snorlax = {"card": ROCKETS_SNORLAX, "energy": [FIRE] * 3, **(attacker or {})}
        return build_test_state([{"active": snorlax, "bench": [RATTATA]}, {"active": {"card": PONYTA, **(defender or {})}, "bench": [RATTATA]}],
                                turn_number=TURN)

    def test_trigger_and_neighbours(self):
        code = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"
        defender = {"trainers": [(DEFENDER, TURN)]}  # 相手が前の番（6）に使った（次の相手の番 7 の終わりまで）
        for attacker, target in (({}, defender), ({}, {"prevent_damage": TURN - 1}), ({"confusion": True}, defender),
                                 ({}, {"card": HAUNTER, "evolved_from": GASTLY})):
            with self.subTest(attacker=attacker, target=target):
                self.assert_rejected(self.board(attacker, target), UseAttack(0, 0), code)
        # 止めない 1: プラスパワーで 30 − 20 = 10（ダメージを与えた）。自分はねむりになる
        boosted = self.assert_proceeds(self.board({"trainers": [(PLUSPOWER, TURN)]}, defender), UseAttack(0, 0))
        self.assertEqual([e["condition"] for e in boosted.log if e["kind"] == "special_condition"], ["sleep"])
        # 止めない 2: 相手をきぜつさせても、ダメージを与えたので自分はねむりになる
        knocked = self.assert_proceeds(self.board(None, {"damage": 30}), UseAttack(0, 0))
        self.assertIn("sleep", [e.get("condition") for e in knocked.log if e["kind"] == "special_condition"])


class CodeListTest(unittest.TestCase):
    def test_every_code_in_the_engine_is_covered_here(self):
        """エンジンの中の ``UNRESOLVED_…`` のコード（既定の UNRESOLVED_RULING を除く）が、このファイルの一覧と同じ。新しいコードを
        加えたら、ここに止まる場合と隣の止まらない場合を加える。v0.16b: 解決の基盤（``kyuura_engine/resolution/``）もエンジンの中なので
        数える（v0.13 の経路を外して、エナジーへんかんの 0 枚の ``UNRESOLVED_RECOVER_ZERO_ENERGY`` は解決の基盤の ``programs.py`` だけに
        なった。v0.15 までは ``effects.py`` にも同じコードがあった）。"""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent / "kyuura_engine"
        found = set()
        for path in root.rglob("*.py"):
            found.update(re.findall(r'"(UNRESOLVED_[A-Z_]+)"', path.read_text(encoding="utf-8")))
        found.discard("UNRESOLVED_RULING")
        self.assertEqual(found, set(ALL_CODES))


if __name__ == "__main__":
    unittest.main()
