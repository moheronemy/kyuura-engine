"""自分へのワザのダメージ（v0.2f）: ピカチュウ（PMCG1-035）の「かじる」「でんげき」。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。カードの記録 PMCG1-035）:

- p.125 のピカチュウ（LV.12/HP40、第1弾）。最新の説明「●かじる」「●でんげき コインを投げて「うら」なら、自分にも10ダメージ。」
- p.320: ダメージの目安に「×」などがなければ「相手の対戦ポケモンに○○ダメージ。」が最初に省略されている。ワザの要素は
  書かれている順番に処理する。ダメージの分類 (1) 相手の対戦ポケモン (3) このワザを使うポケモン
- p.321「8 ワザによるダメージと効果」: ワザによってもたらされたダメージは「ワザによるダメージ」
- p.321「9」: 1 基本 → 2 → 3 弱点 → 4 抵抗力 → 5 ワザを使うポケモンについているカード（プラスパワー）→ 6 →
  7 ワザを受けるポケモンについているカード（ディフェンダー）→ 8。途中の 0・マイナスはかまわない
- p.257 の解説: 自分へのダメージにもプラスパワーは +10、ディフェンダーは -20
- p.322: こんらんで自分が受けるダメージは「弱点・抵抗力」の影響を受ける（ワザの説明による自分へのダメージには
  書かれていないので、弱点・抵抗力が関係する場合は扱わない）
- p.309: 途中で対象がいなくなった内容は無視し、それ以降の内容は無視しない
"""

import copy
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EngineError, IllegalActionError, Phase, PlayTrainer, ResolveDecision, TakePrize,
    UnsupportedError, UseAttack, apply_command, check_invariants, load_card_pool, state_to_dict,
)
from kyuura_engine.cards import pool_from_extract, read_extract, read_verification
from kyuura_engine.effects import (
    DAMAGE_ONLY, DEFAULT_EFFECTS, SELF, AttackEntry, AttackKey, SelfDamageOnTails, damage_opponent_active,
    deal_attack_damage,
)
from kyuura_engine.coins import flip_coins
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import GameResult, Halt

from tests.helpers import (
    DEFENDER, DIGLETT, FIRE, GROWLITHE, H, LIGHTNING, PIKACHU, PLUSPOWER, PONYTA, STARYU, T,
    build_test_state, with_coin_results,
)

GNAW, THUNDER_JOLT = 0, 1
SELF_WEAK = "TEST-PIKACHU-WEAK-TO-LIGHTNING"
SELF_RESISTANT = "TEST-PIKACHU-RESISTS-LIGHTNING"


def full(state):
    return state_to_dict(state, format_version=4)


def hand(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def pikachu_vs(defender, *sides, damage=0, hand_cards=(), bench=(PONYTA,), their_bench=(GROWLITHE,), prizes=6, their_prizes=6,
               energy=(LIGHTNING, FIRE), effects=None, pool=None, card=PIKACHU):
    state = build_test_state([
        {"active": {"card": card, "energy": list(energy), "damage": damage}, "bench": list(bench), "hand": list(hand_cards),
         "prizes": prizes},
        {"active": defender, "bench": list(their_bench), "prizes": their_prizes},
    ], effects=effects, pool=pool)
    return with_coin_results(state, *sides) if sides else state


def play_all(state, card_id, player=0):
    for card in hand(state, player, card_id):
        state = apply_command(state, PlayTrainer(player, card))
        if state.decision is not None:  # ディフェンダー: 対戦ポケモンにつける
            state = apply_command(state, ResolveDecision(player, state.decision.id, (state.players[player].active.pokemon_id,)))
    return state


def thunder_jolt(state, player=0):
    start = len(state.log)
    new = apply_command(state, UseAttack(player, THUNDER_JOLT))
    events = [dict(e) for e in new.log[start:]]
    damages = [e for e in events if e["kind"] == "damage"]
    opponent = next(e for e in damages if e.get("target") is None)
    own = [e for e in damages if e.get("target") == "self"]
    return new, events, opponent, (own[0] if own else None)


# ---------------------------------------------------------------- 登録と照合


class PikachuRegistrationTest(unittest.TestCase):
    def test_registered_attacks(self):
        gnaw = DEFAULT_EFFECTS.attack_entry(PIKACHU, GNAW)
        jolt = DEFAULT_EFFECTS.attack_entry(PIKACHU, THUNDER_JOLT)
        self.assertIs(gnaw.effect, DAMAGE_ONLY)
        self.assertEqual((gnaw.name_ja, gnaw.text_ja), ("かじる", None))
        self.assertIsInstance(jolt.effect, SelfDamageOnTails)
        self.assertEqual((jolt.name_ja, jolt.effect.self_damage, jolt.source), ("でんげき", 10, "P43 p.125"))
        record = read_verification()["cards"][PIKACHU]
        self.assertEqual((record["page"], record["pdf_page"], record["status"]), (125, 127, "一致"))
        self.assertEqual(jolt.play_text_ja, record["latest_description_ja"])
        self.assertEqual(jolt.text_ja, load_card_pool().get(PIKACHU).attacks[THUNDER_JOLT].text_ja)

    def test_card_data_matches_the_book(self):
        pikachu = load_card_pool().get(PIKACHU)
        self.assertTrue(pikachu.supported)
        self.assertEqual((pikachu.hp, pikachu.pokemon_type.value, pikachu.weakness.value, pikachu.resistance, pikachu.retreat_cost),
                         (40, "lightning", "fighting", None, 1))
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier) for a in pikachu.attacks],
                         [("かじる", ["colorless"], 10, None), ("でんげき", ["lightning", "colorless"], 30, None)])

    def test_wrong_registrations_are_detected(self):
        pool = load_card_pool()
        doduo_attack = pool.get("PMCG1-061").attacks[0]  # みだれづき（「×」）
        effects = DEFAULT_EFFECTS.with_attacks("test-bad", {
            AttackKey("PMCG1-061", 0): AttackEntry(SelfDamageOnTails(10), "みだれづき", text_ja=doduo_attack.text_ja),
            AttackKey(PIKACHU, GNAW): AttackEntry(SelfDamageOnTails(10), "かじる"),
        })
        self.assertIn("「×」", effects.attack_problem("PMCG1-061", doduo_attack))
        self.assertIn("説明文のない", effects.attack_problem(PIKACHU, pool.get(PIKACHU).attacks[GNAW]))
        for bad in (0, 15, -10, True):
            with self.assertRaises(ValueError):
                SelfDamageOnTails(bad)


# ---------------------------------------------------------------- 「かじる」と「でんげき」の基本


class ThunderJoltTest(unittest.TestCase):
    def test_gnaw_is_damage_only(self):
        state = pikachu_vs(GROWLITHE)
        fingerprint = rng_fingerprint(state.rng)
        state = apply_command(state, UseAttack(0, GNAW))
        damage = [e for e in state.log if e["kind"] == "damage"][-1]
        self.assertEqual(damage["amount"], 10)
        self.assertEqual(rng_fingerprint(state.rng), fingerprint)  # コインはない

    def test_heads_no_self_damage(self):
        state, events, opponent, own = thunder_jolt(pikachu_vs(GROWLITHE, H))
        self.assertEqual(opponent["amount"], 30)
        self.assertIsNone(own)
        self.assertEqual(state.players[0].active.damage, 0)
        self.assertEqual([e["kind"] for e in events[:3]], ["attack", "damage", "coin_flip"])

    def test_tails_self_damage_in_the_order_written(self):
        """相手に 30 → コイン → 自分に 10（p.320: 省略された「相手に30ダメージ」が最初、要素は書かれている順番）。"""
        state, events, opponent, own = thunder_jolt(pikachu_vs(GROWLITHE, T))
        self.assertEqual([e["kind"] for e in events[:4]], ["attack", "damage", "coin_flip", "damage"])
        self.assertEqual((opponent["amount"], own["amount"]), (30, 10))
        pikachu = state.players[0].active
        self.assertEqual(own, {
            "kind": "damage", "turn": 3, "player": 0, "pokemon": pikachu.card, "amount": 10, "steps": (("1 基本となる計算", 10),),
            "weakness": False, "resistance": False, "total_damage": 10, "target": "self", "pokemon_id": pikachu.pokemon_id,
            "effect": "PMCG1-035#1",
        })
        self.assertEqual(pikachu.damage, 10)
        self.assertNotIn("target", opponent)  # 相手へのダメージの記録は v0.1 と同じ形
        self.assertEqual((state.phase, state.current_player), (Phase.MAIN, 1))

    def test_one_coin_only(self):
        for side in (H, T):
            state = pikachu_vs(GROWLITHE, side)
            expected = copy_rng(state.rng)
            expected.getrandbits(1)
            state, _, _, _ = thunder_jolt(state)
            self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_opponent_weakness_and_resistance(self):
        """相手へのダメージは今までどおり p.321 の順番（ヒトデマン 弱点 雷、ディグダ 抵抗力 雷 -30）。"""
        _, _, opponent, _ = thunder_jolt(pikachu_vs(STARYU, H))
        self.assertEqual((opponent["amount"], opponent["weakness"]), (60, True))
        _, _, opponent, own = thunder_jolt(pikachu_vs(DIGLETT, T))
        self.assertEqual((opponent["amount"], opponent["resistance"]), (0, True))
        self.assertEqual(own["amount"], 10)  # 相手にダメージを与えなかったときも、自分へのダメージの要素は処理する

    def test_insufficient_energy_flips_no_coin(self):
        for energy in ((LIGHTNING,), (FIRE, FIRE)):
            state = pikachu_vs(GROWLITHE, T, energy=energy)
            before, fingerprint = full(state), rng_fingerprint(state.rng)
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, UseAttack(0, THUNDER_JOLT))
            self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")
            self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


# ---------------------------------------------------------------- プラスパワー・ディフェンダー（p.257）


class SelfDamageModifierTest(unittest.TestCase):
    """自分へのダメージ: 同じピカチュウが、ワザを使う立場（プラスパワー 5 段階）と受ける立場（ディフェンダー 7 段階）を持つ。"""

    def jolt(self, pluspowers=0, defenders=0, defender=GROWLITHE, damage=0):
        state = pikachu_vs(defender, damage=damage, hand_cards=[PLUSPOWER] * pluspowers + [DEFENDER] * defenders)
        state = play_all(state, PLUSPOWER)
        state = play_all(state, DEFENDER)
        return thunder_jolt(with_coin_results(state, T))

    def test_combinations(self):
        cases = {
            (0, 0): ([10], 10, 30),
            (1, 0): ([10, 20], 20, 40),
            (2, 0): ([10, 20, 30], 30, 50),
            (0, 1): ([10, -10], 0, 30),
            (0, 2): ([10, -10, -30], 0, 30),
            (1, 1): ([10, 20, 0], 0, 40),
            (2, 1): ([10, 20, 30, 10], 10, 50),
            (1, 2): ([10, 20, 0, -20], 0, 40),
        }
        for (pluspowers, defenders), (steps, amount, to_opponent) in cases.items():
            with self.subTest(pluspowers=pluspowers, defenders=defenders):
                state, _, opponent, own = self.jolt(pluspowers, defenders)
                self.assertEqual([value for _, value in own["steps"]], steps)
                self.assertEqual(own["amount"], amount)
                self.assertEqual(opponent["amount"], to_opponent)  # ピカチュウのディフェンダーは、与えるダメージを変えない
                labels = [label for label, _ in own["steps"]]
                self.assertEqual(labels, ["1 基本となる計算"] + ["5 プラスパワー"] * pluspowers + ["7 ディフェンダー"] * defenders)
                self.assertEqual(len(own.get("modifiers", ())), pluspowers + defenders)
                # 同じカードを二重に数えない（それぞれのカードは 1 回だけ。プラスパワーは 5 段階、ディフェンダーは 7 段階）
                self.assertEqual(len({m[1] for m in own.get("modifiers", ())}), pluspowers + defenders)
                self.assertEqual(sorted(m[0] for m in own.get("modifiers", ())), [5] * pluspowers + [7] * defenders)

    def test_opponent_defender_does_not_reduce_self_damage(self):
        """相手のディフェンダーは、相手が受けるダメージだけを減らす。ピカチュウが自分に与えるダメージは変えない。"""
        state = build_test_state([
            {"active": {"card": PIKACHU, "energy": [LIGHTNING, FIRE]}},
            {"active": GROWLITHE, "hand": [DEFENDER]},
        ], current_player=1, turn_number=4)
        state = play_all(state, DEFENDER, player=1)
        state = apply_command(state, EndTurn(1))
        _, _, opponent, own = thunder_jolt(with_coin_results(state, T))
        self.assertEqual((opponent["amount"], own["amount"]), (10, 10))
        self.assertNotIn("modifiers", own)

    def test_defender_prevents_self_knock_out(self):
        state, events, _, own = self.jolt(defenders=1, damage=30)
        self.assertEqual((own["amount"], own["total_damage"]), (0, 30))
        self.assertNotIn("knock_out", [e["kind"] for e in events])
        self.assertEqual(len(state.players[0].active.trainers), 1)  # 相手の番の終わりまで残る

    def test_pluspower_causes_self_knock_out(self):
        state, events, _, own = self.jolt(pluspowers=1, damage=20)  # 20 + 20 = 40 = HP
        self.assertEqual((own["amount"], own["total_damage"]), (20, 40))
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((ko["player"], len(ko["discarded_trainers"])), (0, 1))  # プラスパワーもいっしょにトラッシュ


# ---------------------------------------------------------------- 自分のきぜつ（p.323）


class SelfKnockOutTest(unittest.TestCase):
    def test_exactly_hp(self):
        state = pikachu_vs(GROWLITHE, T, damage=30)
        pikachu = state.players[0].active
        state, events, _, own = thunder_jolt(state)
        self.assertEqual(own["total_damage"], 40)
        ko = next(e for e in events if e["kind"] == "knock_out")
        self.assertEqual((ko["player"], ko["pokemon"], ko["discarded_energy"]), (0, pikachu.card, tuple(pikachu.energy)))
        self.assertNotIn("simultaneous", ko)  # きぜつしたのは 1 匹
        self.assertIsNone(state.find_pokemon(pikachu.pokemon_id))  # 場を離れたので番号は無効
        self.assertIn(pikachu.card, state.players[0].discard)
        # 相手側のプレイヤー（番でないプレイヤー）がサイドを取る（p.323）
        self.assertEqual((state.phase, state.decision.player), (Phase.TAKE_PRIZE, 1))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.decision.player), (Phase.PROMOTE_ACTIVE, 0))
        state = apply_command(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual((state.phase, state.current_player, len(state.players[1].prizes)), (Phase.MAIN, 1, 5))
        self.assertEqual(check_invariants(state), [])

    def test_one_short_survives(self):
        state, events, _, own = thunder_jolt(pikachu_vs(GROWLITHE, T, damage=20))
        self.assertEqual(own["total_damage"], 30)
        self.assertNotIn("knock_out", [e["kind"] for e in events])

    def test_self_knock_out_without_bench_loses(self):
        state, _, _, _ = thunder_jolt(pikachu_vs(GROWLITHE, T, damage=30, bench=()))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.result.winner, state.result.conditions), (Phase.GAME_OVER, 1, ((1, "OPPONENT_CANNOT_FIELD_ACTIVE"),)))

    def test_opponent_takes_the_last_prize_on_my_turn(self):
        """自分のワザで自分がきぜつし、相手が最後のサイドを取ったら相手の勝ち（ワザを使ったプレイヤーが取るのではない）。"""
        state, _, _, _ = thunder_jolt(pikachu_vs(GROWLITHE, T, damage=30, their_prizes=1))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.phase, state.result.winner, state.result.conditions), (Phase.GAME_OVER, 1, ((1, "ALL_PRIZES_TAKEN"),)))


# ---------------------------------------------------------------- 原典で決められない場合（自分の弱点・抵抗力）


def self_typed_pool():
    """ピカチュウの記録を写して、弱点・抵抗力を自分のタイプ（雷）にしたテスト専用のカード（実在しない）。"""
    extract = copy.deepcopy(read_extract())
    source = next(c for c in extract["cards"] if c["id"] == PIKACHU)
    weak = copy.deepcopy(source)
    weak["id"] = SELF_WEAK
    weak["pokemon"]["weaknesses"] = [{"type": "lightning", "operator": "×", "value": 2}]
    resistant = copy.deepcopy(source)
    resistant["id"] = SELF_RESISTANT
    resistant["pokemon"]["weaknesses"] = []
    resistant["pokemon"]["resistances"] = [{"type": "lightning", "operator": "-", "value": 30}]
    extract["cards"] += [weak, resistant]
    text = source["pokemon"]["attacks"][1]["text"]["ja"]
    effects = DEFAULT_EFFECTS.with_attacks("test-self-typed", {
        AttackKey(card, THUNDER_JOLT): AttackEntry(SelfDamageOnTails(10), "でんげき", text_ja=text) for card in (SELF_WEAK, SELF_RESISTANT)
    })
    return pool_from_extract(extract, effects), effects


class UnresolvedSelfWeaknessTest(unittest.TestCase):
    """自分へのワザのダメージに弱点・抵抗力を計算するかは原典で決められない（p.320〜322）。関係する場合は止める。"""

    def test_stops_before_any_damage_or_coin(self):
        """コインを投げる前に止める。「おもて」が出る乱数でも止まる（「おもて」なら自分へのダメージがないことを理由に、
        投げてから使えるかどうかを決めない。CLAUDE.md のコインの約束）。"""
        pool, effects = self_typed_pool()
        for card, side in ((SELF_WEAK, T), (SELF_WEAK, H), (SELF_RESISTANT, T), (SELF_RESISTANT, H)):
            with self.subTest(card=card, side=side):
                state = pikachu_vs(GROWLITHE, side, card=card, pool=pool, effects=effects)
                before, fingerprint = full(state), rng_fingerprint(state.rng)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, THUNDER_JOLT))
                self.assertEqual(ctx.exception.code, "UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE")
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_error_after_the_coin_keeps_the_original_state(self):
        """コインを投げたあとで止まっても、渡した状態と乱数は変わらない（テスト専用の効果: 投げる前の確認を省いた）。"""

        class NoPreCheck(SelfDamageOnTails):
            implementation_id = "test_no_pre_check"

            def resolve(self, state, use):
                damage_opponent_active(state, use, 30)
                flip_coins(state, use.player, 1, source="attack", effect=str(use.key), card=0)
                deal_attack_damage(state, use, SELF, self.self_damage)

        pool, effects = self_typed_pool()
        text = load_card_pool().get(PIKACHU).attacks[THUNDER_JOLT].text_ja
        effects = effects.with_attacks("test-no-pre-check", {AttackKey(SELF_WEAK, THUNDER_JOLT): AttackEntry(NoPreCheck(10), "でんげき", text_ja=text)})
        state = pikachu_vs(GROWLITHE, T, card=SELF_WEAK, pool=pool, effects=effects)
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(UnsupportedError):
            apply_command(state, UseAttack(0, THUNDER_JOLT))
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


# ---------------------------------------------------------------- 不正な操作は状態も乱数も変えない


class InvalidCommandsTest(unittest.TestCase):
    def assert_rejected(self, state, command, code, error=EngineError):
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(error) as ctx:
            apply_command(state, command)
        self.assertEqual(ctx.exception.code, code, command)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))

    def test_rejections(self):
        state = pikachu_vs(GROWLITHE, T, hand_cards=[LIGHTNING])
        energy = state.players[0].hand[0]
        for command, code in ((UseAttack(2, THUNDER_JOLT), "INVALID_PLAYER"), (UseAttack(1, THUNDER_JOLT), "NOT_YOUR_TURN"),
                              (UseAttack(0, 2), "INVALID_ATTACK"), (AttachEnergy(0, energy, 999), "TARGET_NOT_IN_PLAY"),
                              (ResolveDecision(0, 1, (0,)), "WRONG_PHASE"), (TakePrize(0, 0), "WRONG_PHASE")):
            with self.subTest(command=command):
                self.assert_rejected(state, command, code)
        unregistered = pikachu_vs(GROWLITHE, T, effects=DEFAULT_EFFECTS.without_attacks("test-no-jolt", [AttackKey(PIKACHU, THUNDER_JOLT)]))
        self.assert_rejected(unregistered, UseAttack(0, THUNDER_JOLT), "UNSUPPORTED_ATTACK", UnsupportedError)

    def test_after_the_attack(self):
        state, _, _, _ = thunder_jolt(pikachu_vs(GROWLITHE, T))
        self.assert_rejected(state, UseAttack(0, THUNDER_JOLT), "NOT_YOUR_TURN")  # 番が終わった
        knocked, _, _, _ = thunder_jolt(pikachu_vs(GROWLITHE, T, damage=30))
        self.assert_rejected(knocked, UseAttack(0, THUNDER_JOLT), "WRONG_PHASE")  # サイドの決定を待っている
        self.assert_rejected(knocked, ResolveDecision(0, knocked.decision.id, (0,)), "NOT_YOUR_DECISION")
        self.assert_rejected(knocked, ResolveDecision(1, knocked.decision.id, (99,)), "INVALID_CHOICE")

    def test_finished_and_halted_games(self):
        state = pikachu_vs(GROWLITHE, T)
        state.phase = Phase.GAME_OVER
        state.result = GameResult("win", 0, ((0, "ALL_PRIZES_TAKEN"),))
        self.assert_rejected(state, UseAttack(0, THUNDER_JOLT), "GAME_OVER")
        state = pikachu_vs(GROWLITHE, T)
        state.phase = Phase.HALTED
        state.halt = Halt("UNRESOLVED_MULLIGAN_COMPENSATION", "テスト", ())
        self.assert_rejected(state, UseAttack(0, THUNDER_JOLT), "UNRESOLVED_MULLIGAN_COMPENSATION", UnsupportedError)


if __name__ == "__main__":
    unittest.main()
