"""原典で決められない裁定（``UNRESOLVED_…``）が、ちょうど決められない場合だけを止めることの監査（v0.4e。
docs/unresolved-audit-v0.4e.md）。

v0.4e の時点でエンジンが止める 11 件のコードのそれぞれについて、

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
    EndTurn, EngineError, EvolvePokemon, IllegalActionError, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.conditions import paralysis_problem
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Phase

from tests.helpers import (
    BEEDRILL, BUTTERFREE, CATERPIE, DEFENDER, DEWGONG, DODUO, FEW_BASICS, GRASS, GROWLITHE, H, KAKUNA, METAPOD, PARAS, PLUSPOWER,
    POTION, PONYTA, RATTATA, SEEL, SWITCH, T, VULPIX, WATER, WEEDLE, FIRE, build_test_state, find_seed, uids, with_coin_results,
)
from tests.test_evolution_v0_4a import test_pool

ALL_CODES = (
    "UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_POTION_WITHOUT_DAMAGE", "UNRESOLVED_POTION_UNDAMAGED_TARGET",
    "UNRESOLVED_SWITCH_WITHOUT_BENCH", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER",
    "UNRESOLVED_REPARALYSIS_RECOVERY_TURN", "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED",
    "UNRESOLVED_EVOLUTION_HP", "UNRESOLVED_PREVENTED_COIN_DAMAGE",
)
TURN = 7


def full(state):
    return state_to_dict(state, format_version=8)


class BoundaryTestCase(unittest.TestCase):
    def assert_rejected(self, state, command, code):
        """コマンドの拒否（``UnsupportedError``。状態を返さない）。渡した状態・乱数・ログは変わらない。"""
        before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, command)
        self.assertIs(type(ctx.exception), UnsupportedError)
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
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


class CodeListTest(unittest.TestCase):
    def test_every_code_in_the_engine_is_covered_here(self):
        """エンジンの中の ``UNRESOLVED_…`` のコード（既定の UNRESOLVED_RULING を除く）が、このファイルの一覧と同じ。新しいコードを
        加えたら、ここに止まる場合と隣の止まらない場合を加える。"""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent / "kyuura_engine"
        found = set()
        for path in root.glob("*.py"):
            found.update(re.findall(r'"(UNRESOLVED_[A-Z_]+)"', path.read_text(encoding="utf-8")))
        found.discard("UNRESOLVED_RULING")
        self.assertEqual(found, set(ALL_CODES))


if __name__ == "__main__":
    unittest.main()
