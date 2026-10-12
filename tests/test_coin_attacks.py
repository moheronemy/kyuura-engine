"""コインを投げるワザ（v0.2d）: ドードー（PMCG1-061、第1弾）の「みだれづき」。

根拠:

- 『ポケモンカードオフィシャルブック2000』p.231 のドードーのページ。「ワザ」欄の最新の説明
  「●みだれづき コインを2枚投げ、「おもて」の数×10のダメージ。」、図版 無1・10×・にげる 記載なし・弱点 雷・抵抗力 闘 -30
  （kyuura_engine/data/card_verification.json）
- p.309 ワザを使う手順（2 でエネルギー、6 でワザの説明にしたがって処理する）
- p.319 コイントス、p.320「×」（0 倍になり、ダメージがなくなることもある。特に指定がなければ相手の対戦ポケモン）
- p.321 ダメージ計算の順番（2 段階までで 0 以下なら計算を終える）、p.323 ワザの失敗・きぜつ
- kyuura の記録: NEO-2000-OFFICIAL-RULES、カード PMCG1-061
"""

import copy
import unittest

from kyuura_engine import (
    AttachEnergy, EngineError, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat,
    StateIntegrityError, TakePrize, UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants,
    load_card_pool, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract, read_verification
from kyuura_engine.coins import flip_coins
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEffect, AttackEntry, AttackKey, CoinFlipDamage
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import GameResult, Halt

from tests.helpers import (
    CHARMANDER, DIGLETT, DODUO, FIGHTING, FIRE, GROWLITHE, H, HITMONCHAN, LIGHTNING, POTION, RATTATA, STARYU, T,
    VOLTORB, WATER, build_test_state, with_coin_results,
)

DODUO_KEY = AttackKey(DODUO, 0)
WEAK = "TEST-WEAK-TO-COLORLESS"
RESISTANT = "TEST-RESISTS-COLORLESS"


def full(state):
    return state_to_dict(state, format_version=4)


def test_pool():
    """テスト専用のカード 2 枚を加えたカードの組（ドードーは無色。今の対応カードに、無色が弱点・抵抗力の
    ポケモンはいないので、計算の順番を確かめるために作る。実在のカードではない）。"""
    extract = copy.deepcopy(read_extract())
    staryu = next(c for c in extract["cards"] if c["id"] == STARYU)
    weak = copy.deepcopy(staryu)
    weak["id"] = WEAK
    weak["pokemon"]["weaknesses"] = [{"type": "colorless", "operator": "×", "value": 2}]
    resistant = copy.deepcopy(staryu)
    resistant["id"] = RESISTANT
    resistant["pokemon"]["weaknesses"] = []
    resistant["pokemon"]["resistances"] = [{"type": "colorless", "operator": "-", "value": 30}]
    extract["cards"] += [weak, resistant]
    return pool_from_extract(extract)


TEST_POOL = test_pool()


def doduo_vs(defender, *sides, defender_damage=0, hand=(), prizes=6, energy=(FIRE,), their_bench=(STARYU,)):
    """ドードー（エネルギー 1 枚）がバトル場の盤面。次に投げるコインは ``sides``。"""
    state = build_test_state(
        [
            {"active": {"card": DODUO, "energy": list(energy)}, "bench": [GROWLITHE], "hand": list(hand), "prizes": prizes},
            {"active": {"card": defender, "damage": defender_damage}, "bench": list(their_bench)},
        ],
        pool=TEST_POOL,
    )
    return with_coin_results(state, *sides) if sides else state


def attack(state):
    start = len(state.log)
    new = apply_command(state, UseAttack(0, 0))
    events = [dict(e) for e in new.log[start:]]
    damage = next(e for e in events if e["kind"] == "damage")
    return new, events, damage


# ---------------------------------------------------------------- 登録と照合


class RegistrationTest(unittest.TestCase):
    def test_registered_with_the_verified_latest_description(self):
        entry = DEFAULT_EFFECTS.attack_entry(DODUO, 0)
        self.assertIsInstance(entry.effect, CoinFlipDamage)
        self.assertEqual((entry.effect.coins, entry.effect.damage_per_heads), (2, 10))
        self.assertEqual(entry.name_ja, "みだれづき")
        record = read_verification()["cards"][DODUO]
        self.assertEqual((record["page"], record["pdf_page"]), (231, 233))
        self.assertEqual(entry.play_text_ja, record["latest_description_ja"])
        self.assertEqual(entry.play_text_ja, "コインを2枚投げ、「おもて」の数×10のダメージ。")
        self.assertEqual(entry.source, "P43 p.231")
        # 照合用の文面は kyuura の写しの値（印刷の転記。最新の説明とは書き方が違う。不一致あり）
        attack = load_card_pool().get(DODUO).attacks[0]
        self.assertEqual(entry.text_ja, attack.text_ja)
        self.assertEqual(record["status"], "不一致あり")
        self.assertEqual(record["mismatches"][0]["field"], "pokemon.attacks[0].text.ja")

    def test_card_data_matches_the_book(self):
        doduo = load_card_pool().get(DODUO)
        attack = doduo.attacks[0]
        self.assertTrue(doduo.supported)
        self.assertTrue(load_card_pool().is_playable(DODUO))
        self.assertEqual((doduo.hp, doduo.retreat_cost, doduo.weakness.value, doduo.resistance.value, doduo.resistance_value),
                         (50, 0, "lightning", "fighting", 30))
        self.assertEqual((attack.name_ja, [c.value for c in attack.cost], attack.damage, attack.damage_modifier, attack.damage_display),
                         ("みだれづき", ["colorless"], 10, "×", "10×"))

    def test_wrong_registrations_are_detected(self):
        """登録の誤り（「×」のないワザ、目安の数字と違う、説明文が違う）は使えない。"""
        pool = load_card_pool()
        ponyta_kick = pool.get("PMCG1-016").attacks[0]  # けりとばす 20（「×」なし・説明文なし）
        effects = DEFAULT_EFFECTS.with_attacks("test-bad-coin", {
            AttackKey("PMCG1-016", 0): AttackEntry(CoinFlipDamage(coins=2, damage_per_heads=20), "けりとばす"),
            DODUO_KEY: AttackEntry(CoinFlipDamage(coins=2, damage_per_heads=20), "みだれづき",
                                   text_ja=pool.get(DODUO).attacks[0].text_ja),
        })
        problem = effects.attack_problem("PMCG1-016", ponyta_kick)
        self.assertIn("「×」のない", problem)
        self.assertIn("説明文のない", problem)
        self.assertIn("1 枚あたりのダメージ", effects.attack_problem(DODUO, pool.get(DODUO).attacks[0]))
        wrong_text = DEFAULT_EFFECTS.with_attacks("test-text", {
            DODUO_KEY: AttackEntry(CoinFlipDamage(coins=2, damage_per_heads=10), "みだれづき", text_ja="ちがう文面"),
        })
        self.assertIn("説明文", wrong_text.attack_problem(DODUO, pool.get(DODUO).attacks[0]))
        # 説明文のあるワザを効果のないワザ（DamageOnly）として登録しても使えない
        from kyuura_engine.effects import DAMAGE_ONLY

        as_damage_only = DEFAULT_EFFECTS.with_attacks("test-do", {
            DODUO_KEY: AttackEntry(DAMAGE_ONLY, "みだれづき", text_ja=pool.get(DODUO).attacks[0].text_ja)})
        self.assertIn("効果のないワザ", as_damage_only.attack_problem(DODUO, pool.get(DODUO).attacks[0]))

    def test_invalid_implementation_parameters(self):
        for coins, per in ((0, 10), (-1, 10), (True, 10), (2, 0), (2, 15), (2, -10), (2, 10.0)):
            with self.assertRaises(ValueError, msg=(coins, per)):
                CoinFlipDamage(coins=coins, damage_per_heads=per)


# ---------------------------------------------------------------- ダメージ（p.320・p.321）


class FuryAttackDamageTest(unittest.TestCase):
    def test_heads_count_times_ten(self):
        """「おもて」の数×10。2 枚の結果の順番によらない（p.231・p.320）。"""
        for sides, amount in (((T, T), 0), ((H, T), 10), ((T, H), 10), ((H, H), 20)):
            with self.subTest(sides=sides):
                state, events, damage = attack(doduo_vs(STARYU, *sides))
                self.assertEqual([e["result"] for e in events if e["kind"] == "coin_flip"], [s.value for s in sides])
                self.assertEqual(damage["amount"], amount)
                self.assertEqual(damage["steps"], (("1 基本となる計算", amount),))
                self.assertEqual(state.players[1].active.damage, amount)

    def test_all_tails_is_no_damage_not_a_failure(self):
        """「おもて」0 枚: 基本となるダメージ 0 → 2 段階までで 0 以下なので計算を終え、「ダメージを与えなかった」（p.321）。

        ワザの「失敗」（p.323）ではないが、どちらでもワザは使ったことになり、番は終わる（p.309）。
        """
        state, events, damage = attack(doduo_vs(STARYU, T, T, defender_damage=10))
        self.assertEqual([e["kind"] for e in events[:4]], ["attack", "coin_flip", "coin_flip", "damage"])
        self.assertEqual((damage["amount"], damage["total_damage"], damage["stopped_after_step_2"]), (0, 10, True))
        self.assertNotIn("modifiers", damage)
        self.assertEqual((damage["weakness"], damage["resistance"]), (False, False))
        self.assertEqual(state.players[1].active.damage, 10)
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))  # 番が終わった
        self.assertIn("turn_end", [e["kind"] for e in events])

    def test_weakness_doubles_the_heads_damage(self):
        """弱点は 3 段階（2 倍）。「おもて」0 枚なら 2 段階で終えるので、弱点は計算しない（p.321）。"""
        for sides, amount, applied in (((H, H), 40, True), ((H, T), 20, True), ((T, T), 0, False)):
            with self.subTest(sides=sides):
                _, _, damage = attack(doduo_vs(WEAK, *sides))
                self.assertEqual((damage["amount"], damage["weakness"]), (amount, applied))

    def test_resistance_can_bring_it_to_zero(self):
        """抵抗力は 4 段階（-30）。途中がマイナスでもよく、最後に 0 以下なら「ダメージを与えなかった」（p.319・p.321）。

        これは 2 段階で終えた場合（「おもて」0 枚）とは区別する（``stopped_after_step_2`` がない）。
        """
        _, _, damage = attack(doduo_vs(RESISTANT, H, H))
        self.assertEqual((damage["amount"], damage["resistance"]), (0, True))
        self.assertEqual(damage["steps"], (("1 基本となる計算", 20), ("4 抵抗力", -10)))
        self.assertNotIn("stopped_after_step_2", damage)
        _, _, damage = attack(doduo_vs(RESISTANT, T, T))
        self.assertEqual((damage["amount"], damage["resistance"], damage["stopped_after_step_2"]), (0, False, True))

    def test_any_energy_pays_the_colorless_cost(self):
        for energy in (FIRE, WATER, LIGHTNING, FIGHTING):
            _, _, damage = attack(doduo_vs(STARYU, H, H, energy=(energy,)))
            self.assertEqual(damage["amount"], 20)

    def test_without_energy_the_attack_cannot_be_used_and_no_coin_is_flipped(self):
        state = doduo_vs(STARYU, H, H, energy=())
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


class DoduoAsDefenderTest(unittest.TestCase):
    """ドードーの弱点（雷）・抵抗力（闘 -30）（p.231 の図版、p.315・p.321）。"""

    def hit(self, attacker, energy, index=0):
        state = build_test_state([{"active": {"card": attacker, "energy": energy}}, {"active": DODUO, "bench": [DODUO]}])
        state = apply_command(state, UseAttack(0, index))
        return next(e for e in state.log if e["kind"] == "damage")

    def test_weakness_lightning(self):
        self.assertEqual(self.hit(VOLTORB, [LIGHTNING])["amount"], 20)  # たいあたり 10 → 20

    def test_resistance_fighting(self):
        self.assertEqual(self.hit(DIGLETT, [FIGHTING])["amount"], 0)  # あなをほる 10 → -20 → 0
        self.assertEqual(self.hit(HITMONCHAN, [FIGHTING, FIGHTING, FIGHTING], index=1)["amount"], 10)  # 40 → 10

    def test_retreat_costs_nothing(self):
        state = build_test_state([{"active": DODUO, "bench": [STARYU]}, {"active": STARYU}])
        state = apply_command(state, Retreat(0, (), state.players[0].bench[0].card))
        self.assertEqual(state.card_def(state.players[0].active.card).id, STARYU)


# ---------------------------------------------------------------- きぜつ・サイド・勝ち（p.323）


class KnockOutTest(unittest.TestCase):
    def test_two_heads_knock_out_and_take_a_prize(self):
        """コラッタ（HP30）にダメージ 10 → みだれづき 20 で HP 以上 → きぜつ → サイド（p.323）。"""
        state, events, damage = attack(doduo_vs(RATTATA, H, H, defender_damage=10))
        self.assertEqual(damage["total_damage"], 30)
        knock_out = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual(knock_out["player"], 1)
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        # コインはサイドの決定の前に投げ終わっている。決定に答えても乱数は使わない
        fingerprint = rng_fingerprint(state.rng)
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)
        self.assertEqual(len(state.players[0].prizes), 5)

    def test_one_head_is_not_enough(self):
        state, events, damage = attack(doduo_vs(RATTATA, H, T, defender_damage=10))
        self.assertEqual(damage["total_damage"], 20)
        self.assertNotIn("knock_out", [e["kind"] for e in events])
        self.assertEqual(state.phase, Phase.MAIN)

    def test_last_prize_wins(self):
        state, _, _ = attack(doduo_vs(RATTATA, H, H, defender_damage=10, prizes=1))
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertEqual((state.result.winner, state.result.conditions), (0, ((0, "ALL_PRIZES_TAKEN"),)))

    def test_knock_out_with_no_bench_wins(self):
        state, _, _ = attack(doduo_vs(RATTATA, T, H, defender_damage=20, their_bench=()))
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.phase, Phase.GAME_OVER)
        self.assertIn((0, "OPPONENT_CANNOT_FIELD_ACTIVE"), state.result.conditions)


# ---------------------------------------------------------------- ログ


class CoinLogInAttackTest(unittest.TestCase):
    def test_events_name_the_player_card_attack_and_pokemon_id(self):
        state = doduo_vs(STARYU, H, T)
        doduo = state.players[0].active
        new, events, _ = attack(state)
        flips = [e for e in events if e["kind"] == "coin_flip"]
        self.assertEqual(flips, [
            {"kind": "coin_flip", "turn": 3, "player": 0, "source": "attack", "effect": "PMCG1-061#0",
             "card": doduo.card, "pokemon_id": doduo.pokemon_id, "number": 1, "count": 2, "result": "heads"},
            {"kind": "coin_flip", "turn": 3, "player": 0, "source": "attack", "effect": "PMCG1-061#0",
             "card": doduo.card, "pokemon_id": doduo.pokemon_id, "number": 2, "count": 2, "result": "tails"},
        ])
        # card はカードの uid、pokemon_id は場のポケモンの番号（別の番号）
        self.assertEqual(new.cards[flips[0]["card"]].card_id, DODUO)
        self.assertEqual(new.find_pokemon(flips[0]["pokemon_id"])[1].card, doduo.card)
        self.assertNotEqual(doduo.card, doduo.pokemon_id)
        self.assertEqual([e["kind"] for e in events[:4]], ["attack", "coin_flip", "coin_flip", "damage"])

    def test_damage_event_keeps_the_v0_1_shape(self):
        """「おもて」が 1 枚以上なら、ダメージの記録は v0.1 と同じ項目（2 段階で終えたときだけ項目が増える）。"""
        _, _, damage = attack(doduo_vs(STARYU, H, H))
        self.assertEqual(set(damage), {"kind", "turn", "player", "pokemon", "amount", "steps", "weakness", "resistance", "total_damage"})


# ---------------------------------------------------------------- 不正な操作は乱数を使わない


class InvalidCommandsUseNoRandomnessTest(unittest.TestCase):
    """拒否した操作は、状態も乱数も変えない。その後に正しくワザを使うと、拒否がなかったときと同じコインになる。"""

    def assert_rejected(self, state, command, code=None, error=EngineError):
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        if code is not None:
            self.assertEqual(ctx.exception.code, code)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_rejections_in_main(self):
        state = doduo_vs(STARYU, H, T, hand=[FIRE])
        reference = attack(state)[1]
        energy = state.players[0].hand[0]
        cases = [
            (UseAttack(2, 0), "INVALID_PLAYER"),
            (UseAttack(-1, 0), "INVALID_PLAYER"),
            (UseAttack(1, 0), "NOT_YOUR_TURN"),
            (UseAttack(0, 1), "INVALID_ATTACK"),
            (UseAttack(0, -1), "INVALID_ATTACK"),
            (AttachEnergy(0, energy, 999), "TARGET_NOT_IN_PLAY"),
            (Retreat(0, (), 999), "NOT_ON_BENCH"),
            (PlayTrainer(0, 999), "CARD_NOT_IN_HAND"),
            (ResolveDecision(0, 1, (1,)), "WRONG_PHASE"),
            (TakePrize(0, 0), "WRONG_PHASE"),
            # v0.4a から進化を処理する（手札のエネルギーは進化カードではない。v0.3d までは UNSUPPORTED_ACTION）
            (EvolvePokemon(0, energy, state.players[0].active.pokemon_id), "NOT_EVOLUTION_CARD"),
            (UsePokemonPower(0, state.players[0].active.card), "UNSUPPORTED_ACTION"),
        ]
        for command, code in cases:
            with self.subTest(command=command):
                self.assert_rejected(state, command, code)
        self.assertEqual(attack(state)[1], reference)

    def test_unregistered_and_unsupported_attacks(self):
        effects = DEFAULT_EFFECTS.without_attacks("test-no-doduo", [DODUO_KEY])
        state = build_test_state([{"active": {"card": DODUO, "energy": [FIRE]}}, {"active": STARYU}], effects=effects)
        self.assert_rejected(state, UseAttack(0, 0), "UNSUPPORTED_ATTACK", UnsupportedError)
        state = build_test_state([{"active": {"card": CHARMANDER, "energy": [FIRE, FIRE]}}, {"active": STARYU}])
        self.assert_rejected(state, UseAttack(0, 1), "UNSUPPORTED_ATTACK", UnsupportedError)  # ひのこ（未登録）

    def test_pending_decision_rejects_attacks(self):
        state = doduo_vs(STARYU, H, H, hand=[POTION])
        state.players[0].active.damage = 20
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        self.assertEqual(state.phase, Phase.DECISION)
        self.assert_rejected(state, UseAttack(0, 0), "WRONG_PHASE")
        # 決定に答えても乱数は使わない。そのあとでワザを使うと、決めたとおりのコイン
        fingerprint = rng_fingerprint(state.rng)
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].active.pokemon_id,)))
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)
        _, _, damage = attack(state)
        self.assertEqual(damage["amount"], 20)

    def test_take_prize_phase_rejects_attacks(self):
        state, _, _ = attack(doduo_vs(RATTATA, H, H, defender_damage=10))
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assert_rejected(state, UseAttack(0, 0), "WRONG_PHASE")
        self.assert_rejected(state, UseAttack(1, 0), "WRONG_PHASE")

    def test_game_over_and_halted(self):
        state = doduo_vs(STARYU, H, H)
        state.phase = Phase.GAME_OVER
        state.result = GameResult("win", 0, ((0, "ALL_PRIZES_TAKEN"),))
        self.assertEqual(check_invariants(state), [])
        self.assert_rejected(state, UseAttack(0, 0), "GAME_OVER")
        state = doduo_vs(STARYU, H, H)
        state.phase = Phase.HALTED
        state.halt = Halt("UNRESOLVED_MULLIGAN_COMPENSATION", "テスト", ())
        self.assert_rejected(state, UseAttack(0, 0), "UNRESOLVED_MULLIGAN_COMPENSATION", UnsupportedError)

    def test_second_attack_in_the_same_turn_is_impossible(self):
        """ワザを使ったら番が終わる（p.309）ので、同じ番に 2 回は投げられない。"""
        state, _, _ = attack(doduo_vs(STARYU, T, T))
        self.assertEqual(state.current_player, 1)
        self.assert_rejected(state, UseAttack(0, 0), "NOT_YOUR_TURN")


class ErrorAfterFlippingTest(unittest.TestCase):
    """コインを投げたあとで処理が止まっても、渡した状態の乱数は進まない（複製した状態で処理する）。

    ここで使う効果はテスト専用（製品の登録表には入れない）。
    """

    class FlipThenRaise(AttackEffect):
        implementation_id = "test_flip_then_raise"

        def __init__(self, error):
            self.error = error

        def resolve(self, state, use):
            flip_coins(state, use.player, 2, source="attack", effect=str(use.key), card=0)
            raise self.error

    class BadCount(AttackEffect):
        implementation_id = "test_bad_count"

        def resolve(self, state, use):
            flip_coins(state, use.player, 0, source="attack", effect=str(use.key), card=0)

    def state_with(self, effect):
        text = load_card_pool().get(DODUO).attacks[0].text_ja
        effects = DEFAULT_EFFECTS.with_attacks("test-error", {DODUO_KEY: AttackEntry(effect, "みだれづき", text_ja=text)})
        return build_test_state([{"active": {"card": DODUO, "energy": [FIRE]}}, {"active": STARYU}], effects=effects)

    def check(self, effect, error):
        state = self.state_with(effect)
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(error):
            apply_command(state, UseAttack(0, 0))
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_unresolved_case_found_after_flipping(self):
        """原典で決められない場合（UnsupportedError）。"""
        self.check(self.FlipThenRaise(UnsupportedError("UNRESOLVED_TEST", "テスト")), UnsupportedError)

    def test_engine_bug_after_flipping(self):
        """エンジンの不具合（StateIntegrityError など、プレイヤーの操作の誤りではないもの）。"""
        self.check(self.FlipThenRaise(StateIntegrityError(["テスト"])), StateIntegrityError)

    def test_invalid_coin_count_is_not_a_player_error(self):
        """効果の実装の誤り（枚数 0）は ValueError で、プレイヤーの操作の誤り（EngineError）とは区別する。"""
        self.check(self.BadCount(), ValueError)
        with self.assertRaises(ValueError):
            apply_command(self.state_with(self.BadCount()), UseAttack(0, 0))
        self.assertFalse(issubclass(ValueError, EngineError))


if __name__ == "__main__":
    unittest.main()
