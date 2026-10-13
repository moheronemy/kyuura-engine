"""サカキのワンリキー（PMCG6-057）・サカキのゴーリキー（PMCG6-059）・サカキのカイリキー（PMCG6-061）のカードとワザ（v0.11。
docs/giovanni-machamp-line-v0.11.md の L1〜L14）。

『ポケモンカードオフィシャルブック2000』p.189（サカキのワンリキー）・p.191（サカキのゴーリキー）・p.193（サカキのカイリキー）の最新の説明と
解説、p.310（進化）・p.319〜p.321（ダメージ・「×」「+」のワザ・ダメージの計算）にしたがう。

- チョップ（無。10）: 説明文なし（DamageOnly）。
- いかりのスーパーパンチ（闘闘。20×）: 「コインを投げて「おもて」なら、自分にのっているダメージカウンターの数×20のダメージ。」
- いちかばちか（闘。60）: 「コインを投げて「うら」なら、相手にはダメージを与えず、自分に100ダメージ。」
- じごくがため（闘闘無。20+）: 「コインを投げて「おもて」なら、20ダメージを追加して、相手を「マヒ」状態にする。」（v0.8 のねばりつくと同じ）
- ハリケーンパンチ（闘闘闘無。30×）: 「コインを4枚投げ、「おもて」の数×30のダメージ。」

盤面は ``build_test_state`` で直接作る（1 つの規定を確かめるテスト）。こんじょうは tests/test_guts_v0_11.py。
"""

import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, EvolvePokemon, IllegalActionError, PlayTrainer, UnsupportedError, UseAttack, apply_command, check_invariants,
    load_card_pool,
)
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.effects import (
    AttackKey, AttackUse, CoinBonusDamageAndParalyze, CoinFlipDamage, CoinHeadsDamagePerOwnCounter, DamageOnly, DamageProfile,
    SelfDamageInsteadOnTails,
)

from tests.helpers import (
    CATERPIE, DEFENDER, FIGHTING, GASTLY, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, H, HAUNTER, HITMONCHAN, MACHAMP,
    MACHOKE, MACHOP, METAPOD, PLUSPOWER, PONYTA, RATTATA, T, build_test_state, coin_events, uids, with_coin_results,
)
from tests.test_transparency_v0_9 import rng_draws

TURN = 7


def gmachop(**extra):
    return {"card": GIOVANNIS_MACHOP, "energy": [FIGHTING] * 2, **extra}


def gmachoke(**extra):
    return {"card": GIOVANNIS_MACHOKE, "evolved_from": GIOVANNIS_MACHOP, "energy": [FIGHTING] * 3, **extra}


def gmachamp(**extra):
    return {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "energy": [FIGHTING] * 4, **extra}


def board(attacker, defender=HITMONCHAN, *, hand0=(), turn=TURN):
    """プレイヤー 0 がワザを使う。相手のバトル場は既定でエビワラー（HP 70・闘・弱点 超。こんじょう・はんげきを持たない）。"""
    return build_test_state([
        {"active": attacker, "bench": [PONYTA], "hand": list(hand0)},
        {"active": defender, "bench": [RATTATA]},
    ], turn_number=turn)


def run(state, command, *sides):
    start = with_coin_results(state, *sides) if sides else state
    new = apply_command(start, command)
    assert check_invariants(new) == []
    return new, [dict(e) for e in new.log[len(start.log):]], rng_draws(start, new)


def damages(events):
    return [(e["player"], e["amount"], e.get("target", "opponent_active")) for e in events if e["kind"] == "damage"]


class CardDataTest(unittest.TestCase):
    """L1・L2: kyuura の写し（kyuura ecb2d694）と『オフィシャルブック2000』の照合の記録・登録。"""

    def test_cards(self):
        pool = load_card_pool()
        machop, machoke, machamp = pool.get(GIOVANNIS_MACHOP), pool.get(GIOVANNIS_MACHOKE), pool.get(GIOVANNIS_MACHAMP)
        self.assertEqual((machop.name_ja, machop.hp, machop.is_basic_pokemon, machop.retreat_cost), ("サカキのワンリキー", 50, True, 1))
        self.assertEqual((machoke.name_ja, machoke.hp, machoke.evolves_from, machoke.retreat_cost), ("サカキのゴーリキー", 80, "サカキのワンリキー", 2))
        self.assertEqual((machamp.name_ja, machamp.hp, machamp.evolves_from, machamp.retreat_cost), ("サカキのカイリキー", 100, "サカキのゴーリキー", 3))
        self.assertTrue(machamp.is_stage2_pokemon)
        self.assertEqual([(a.name_ja, a.damage, a.damage_modifier) for a in machop.attacks], [("チョップ", 10, None), ("いかりのスーパーパンチ", 20, "×")])
        self.assertEqual([(a.name_ja, a.damage, a.damage_modifier) for a in machoke.attacks], [("いちかばちか", 60, None), ("じごくがため", 20, "+")])
        self.assertEqual([(a.name_ja, a.damage, a.damage_modifier) for a in machamp.attacks], [("ハリケーンパンチ", 30, "×")])
        self.assertEqual(read_extract()["pool_v0_11"], [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP])
        self.assertNotIn(GIOVANNIS_MACHAMP, read_extract()["reference_only"])

    def test_registrations(self):
        expected = {
            (GIOVANNIS_MACHOP, 0): DamageOnly, (GIOVANNIS_MACHOP, 1): CoinHeadsDamagePerOwnCounter, (GIOVANNIS_MACHOKE, 0): SelfDamageInsteadOnTails,
            (GIOVANNIS_MACHOKE, 1): CoinBonusDamageAndParalyze, (GIOVANNIS_MACHAMP, 0): CoinFlipDamage,
        }
        pool = load_card_pool()
        for (card, index), cls in expected.items():
            with self.subTest(card=card, index=index):
                self.assertIsInstance(DEFAULT_EFFECTS.attack_entry(card, index).effect, cls)
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, pool.get(card).attacks[index]))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHAMP, 0).effect, CoinFlipDamage(coins=4, damage_per_heads=30))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHOKE, 1).effect, CoinBonusDamageAndParalyze(bonus=20))

    def test_verification_records(self):
        records = read_verification()["cards"]
        self.assertEqual((records[GIOVANNIS_MACHOP]["page"], records[GIOVANNIS_MACHOKE]["page"], records[GIOVANNIS_MACHAMP]["page"]), (189, 191, 193))
        self.assertEqual(records[GIOVANNIS_MACHOP]["latest_description_ja"], DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHOP, 1).play_text_ja)
        self.assertEqual(records[GIOVANNIS_MACHOKE]["latest_description_ja"]["0"], DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHOKE, 0).play_text_ja)
        self.assertEqual(records[GIOVANNIS_MACHAMP]["latest_description_ja"], DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHAMP, 0).play_text_ja)
        self.assertEqual(records[GIOVANNIS_MACHAMP]["power_latest_description_ja"]["0"], DEFAULT_EFFECTS.power_entry(GIOVANNIS_MACHAMP, 0).play_text_ja)


class ChopTest(unittest.TestCase):
    def test_chop(self):
        """チョップ（無）10。説明文なし（p.189）。"""
        new, events, draws = run(board(gmachop()), UseAttack(0, 0))
        self.assertEqual((damages(events), draws), ([(1, 10, "opponent_active")], 0))


class FuryPunchTest(unittest.TestCase):
    """L3〜L5: いかりのスーパーパンチ（p.189）。"""

    def test_heads_counts_own_counters(self):
        """「おもて」なら、自分にのっているダメージカウンターの数（30 → 3 個）× 20 = 60（p.320 の「×」）。コイン 1 枚（ワザを使った側）。"""
        new, events, draws = run(board(gmachop(damage=30)), UseAttack(0, 1), H)
        self.assertEqual(damages(events), [(1, 60, "opponent_active")])
        self.assertEqual((draws, [(c["source"], c["player"], c["result"]) for c in coin_events(new, len(new.log) - len(events))]),
                         (1, [("attack", 0, "heads")]))

    def test_tails_and_no_counters_deal_no_damage(self):
        """「うら」なら 0、カウンターがなければ「おもて」でも 0（p.189 の解説）。基本となるダメージが 0 なので 2 段階で計算を終え、ダメージを
        与えなかった（プラスパワーの +10 も計算しない。p.321）。"""
        for spec, side in ((gmachop(damage=30), T), (gmachop(), H)):
            with self.subTest(spec=spec, side=side):
                new, events, _ = run(board(spec), UseAttack(0, 1), side)
                self.assertEqual(damages(events), [(1, 0, "opponent_active")])
                self.assertTrue(next(e for e in events if e["kind"] == "damage")["stopped_after_step_2"])
                self.assertEqual(new.players[1].active.damage, 0)
        state = board(gmachop(), hand0=[PLUSPOWER])
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        new, events, _ = run(state, UseAttack(0, 1), H)
        self.assertEqual(new.players[1].active.damage, 0)

    def test_prevented_defender_is_unresolved(self):
        """「ダメージを受けない」状態（かたまる）の相手には、コインがダメージの量だけを決めるので、みだれづきと同じくコインの前に止める
        （UNRESOLVED_PREVENTED_COIN_DAMAGE。v0.4b）。"""
        state = board(gmachop(damage=30), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(state, UseAttack(0, 1))
        self.assertEqual(raised.exception.code, "UNRESOLVED_PREVENTED_COIN_DAMAGE")

    def test_damage_profile(self):
        state = board(gmachop(damage=40))
        use = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(GIOVANNIS_MACHOP, 1))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHOP, 1).effect.damage_profile(state, use), DamageProfile(opponent=(0, 80)))


class RiskyAttackTest(unittest.TestCase):
    """L6〜L10: いちかばちか（p.191）。"""

    def test_heads_damages_the_opponent(self):
        new, events, draws = run(board(gmachoke()), UseAttack(0, 0), H)
        self.assertEqual((damages(events), draws), ([(1, 60, "opponent_active")], 1))
        self.assertEqual(new.players[0].active.damage, 0)

    def test_tails_no_opponent_damage_and_100_to_itself(self):
        """「うら」なら相手にはダメージを与えず（相手へのダメージの要素がない）、自分に 100（HP 80 なのできぜつ。サイドは相手）。"""
        new, events, _ = run(board(gmachoke()), UseAttack(0, 0), T)
        self.assertEqual(damages(events), [(0, 100, "self")])
        self.assertEqual(new.players[1].active.damage, 0)
        self.assertEqual((new.decision.kind, new.decision.player), ("take_prize", 1))

    def test_two_defenders_reduce_the_self_damage(self):
        """自分へのダメージもワザによるダメージなので、ディフェンダーで減る（p.191 の解説「きぜつしないためには「ディフェンダー」を2枚つけて
        ようやくです」: 100 − 20 − 20 = 60 < 80）。"""
        new, events, _ = run(board(gmachoke(trainers=[(DEFENDER, TURN + 1), (DEFENDER, TURN + 1)])), UseAttack(0, 0), T)
        self.assertEqual(damages(events), [(0, 60, "self")])
        self.assertEqual(new.players[0].active.damage, 60)

    def test_transparency_is_not_checked_on_tails(self):
        """「うら」では相手はダメージを受けない（要素がない）ので、相手のゴーストの「とうめい」のコインはない。「おもて」なら判定がある。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY}
        _, events, draws = run(board(gmachoke(), haunter), UseAttack(0, 0), T)
        self.assertEqual(([e["kind"] for e in events if e["kind"] == "evade_check"], draws), ([], 1))
        _, events, draws = run(board(gmachoke(), haunter), UseAttack(0, 0), H, T)
        self.assertEqual(([e["kind"] for e in events if e["kind"] == "evade_check"], draws), (["evade_check"], 2))

    def test_strikes_back_only_on_heads(self):
        """第1弾のカイリキーの「はんげき」は、相手のワザのダメージを受けたとき（「おもて」）だけ。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE]}
        new, events, _ = run(board(gmachoke(), machamp), UseAttack(0, 0), H)
        self.assertEqual([e["kind"] for e in events if e["kind"] == "counterattack"], ["counterattack"])
        new, events, _ = run(board(gmachoke(), machamp), UseAttack(0, 0), T)
        self.assertEqual([e["kind"] for e in events if e["kind"] == "counterattack"], [])

    def test_c18_uses_only_outcomes_that_can_happen(self):
        """v0.10 の C18 の判定は、同じコインの結果でいっしょに起こる組（DamageProfile.pairs）で確かめる。サカキのゴーリキー（ディフェンダー
        2 枚・ダメージ 10）: 「おもて」なら第1弾のカイリキー（ダメージ 40）は 60 できぜつするが、「はんげき」10 でゴーリキーは 20（きぜつ
        しない）。「うら」なら相手はダメージを受けず「はんげき」もない（自分への 60 で 70）。どちらの結果でも同時のきぜつの問いは起こらない
        ので止めない（独立に組み合わせると、起こらない「おもて」の相手のきぜつと「うら」の自分への 60 を組にして止めてしまう）。ダメージ
        70 なら「おもて」で「はんげき」だけできぜつするので止める（C18 のまま）。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "damage": 40}
        defended = gmachoke(damage=10, trainers=[(DEFENDER, TURN + 1), (DEFENDER, TURN + 1)])
        new, events, _ = run(board(defended, machamp), UseAttack(0, 0), H)
        self.assertEqual((new.players[0].active.damage, new.decision.kind), (20, "take_prize"))
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(board(gmachoke(damage=70), machamp), UseAttack(0, 0))
        self.assertEqual(raised.exception.code, "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        state = board(gmachoke())
        use = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(GIOVANNIS_MACHOKE, 0))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(GIOVANNIS_MACHOKE, 0).effect.damage_profile(state, use).pairs(), ((60, 0), (None, 100)))


class HeadlockTest(unittest.TestCase):
    """L11: じごくがため（p.191。ねばりつくと同じ説明。CoinBonusDamageAndParalyze(20)）。"""

    def test_heads_and_tails(self):
        new, events, _ = run(board(gmachoke()), UseAttack(0, 1), H)
        self.assertEqual(damages(events), [(1, 40, "opponent_active")])
        self.assertTrue(new.players[1].active.conditions.paralyzed)
        new, events, _ = run(board(gmachoke()), UseAttack(0, 1), T)
        self.assertEqual(damages(events), [(1, 20, "opponent_active")])
        self.assertFalse(new.players[1].active.conditions.paralyzed)


class HurricanePunchTest(unittest.TestCase):
    """L12・L13: ハリケーンパンチ（p.193。「なんと4回もコイントスのできるワザです。…最大で120ダメージ」）。"""

    def test_four_coins(self):
        """コイン 4 枚（ワザを使った側。乱数を 4 回）、「おもて」の数 × 30。HP 100 の相手（第1弾のカイリキー以外にする）に。"""
        target = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE]}
        for sides, amount in (((H, H, H, H), 120), ((H, T, H, T), 60), ((T, T, T, T), 0), ((T, T, T, H), 30)):
            with self.subTest(sides=sides):
                state = board(gmachamp(), target)
                new, events, draws = run(state, UseAttack(0, 0), *sides)
                coins = [e for e in events if e["kind"] == "coin_flip"][:4]
                self.assertEqual([c["result"] for c in coins], ["heads" if s is H else "tails" for s in sides])
                self.assertEqual({(c["source"], c["player"], c["effect"]) for c in coins}, {("attack", 0, f"{GIOVANNIS_MACHAMP}#0")})
                self.assertEqual(damages(events), [(1, amount, "opponent_active")])
                self.assertEqual(draws, 4)  # 120 でサカキのカイリキーは HP 以上になり、こんじょうの決定を待つ（コインはまだ）

    def test_prevented_defender_is_unresolved(self):
        state = board(gmachamp(), {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1})
        with self.assertRaises(UnsupportedError) as raised:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(raised.exception.code, "UNRESOLVED_PREVENTED_COIN_DAMAGE")


class EvolutionTest(unittest.TestCase):
    """L14: サカキのワンリキー → サカキのゴーリキー → サカキのカイリキー（p.310。進化元の名前で決まる）。第1弾のワンリキー・ゴーリキー・
    カイリキーとはたがいに進化できない。"""

    def test_chain(self):
        state = build_test_state([
            {"active": {"card": GIOVANNIS_MACHOP, "played_turn": 1}, "bench": [{"card": MACHOP, "played_turn": 1}],
             "hand": [GIOVANNIS_MACHOKE, MACHOKE, GIOVANNIS_MACHAMP]},
            {"active": PONYTA},
        ], turn_number=5)
        gpid, mpid = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
        with self.assertRaises(IllegalActionError):
            apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", GIOVANNIS_MACHOKE)[0], mpid))  # ワンリキーからは進化できない
        with self.assertRaises(IllegalActionError):
            apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", MACHOKE)[0], gpid))  # サカキのワンリキーからゴーリキーへは進化できない
        once = apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", GIOVANNIS_MACHOKE)[0], gpid))
        self.assertEqual(once.cards[once.players[0].active.card].card_id, GIOVANNIS_MACHOKE)
        later = build_test_state([
            {"active": gmachoke(), "bench": [RATTATA], "hand": [GIOVANNIS_MACHAMP, MACHAMP]},
            {"active": PONYTA},
        ], turn_number=TURN)
        pid = later.players[0].active.pokemon_id
        with self.assertRaises(IllegalActionError):
            apply_command(later, EvolvePokemon(0, uids(later, 0, "hand", MACHAMP)[0], pid))
        done = apply_command(later, EvolvePokemon(0, uids(later, 0, "hand", GIOVANNIS_MACHAMP)[0], pid))
        self.assertEqual((done.cards[done.players[0].active.card].card_id, done.players[0].active.pokemon_id), (GIOVANNIS_MACHAMP, pid))
        self.assertEqual(len(done.players[0].active.evolution_stack), 2)


if __name__ == "__main__":
    unittest.main()
