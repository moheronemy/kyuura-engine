"""ワンリキー（PMCG1-053）→ ゴーリキー（PMCG1-055）→ カイリキー（PMCG1-057）のワザと進化（v0.10。docs/machamp-line-v0.10.md の M1〜M12）。

- ワンリキー「けたぐり」（闘。20）: 説明文なし（p.189。v0.1 から効果のないワザとして登録）。
- ゴーリキー「からてチョップ」（闘闘無。50−）: 最新の説明（p.190）「このワザのダメージは、自分にのっているダメージカウンターの数×10だけ、
  小さくなる。」（p.186 のタケシのマンキーも同じ）。``DamageReducedByOwnCounters(10)``。
- ゴーリキー「じごくぐるま」（闘闘無無。60）: 最新の説明（p.190）「自分にも20ダメージ。」。``DamageAndSelfDamage(20)``。
- カイリキー「ちきゅうなげ」（闘闘闘無。60）: 説明文なし（p.192）。効果のないワザ。

ダメージの計算は p.321（1 段階の基本となるダメージ → 2 段階までで 0 以下なら終わる → 弱点・抵抗力 → プラスパワー・ディフェンダー）、
自分へのダメージは p.320 の (3)・p.321・p.90（プラスパワー・弱点・抵抗力の影響を受ける）・p.257（ディフェンダー）。盤面は
``build_test_state`` で直接作る。
"""

import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, EvolvePokemon, IllegalActionError, PlayTrainer, UseAttack, apply_command, check_invariants, load_card_pool,
)
from kyuura_engine.effects import AttackKey, DamageAndSelfDamage, DamageOnly, DamageReducedByOwnCounters, DamageProfile, AttackUse

from tests.helpers import (
    BUTTERFREE, CATERPIE, DEFENDER, FIGHTING, GIOVANNIS_MACHAMP, MACHAMP, MACHOKE, MACHOP, METAPOD, PIKACHU, PLUSPOWER, PONYTA,
    RATTATA, build_test_state, uids,
)
from kyuura_engine.cards import read_verification

TURN = 7


def machoke(**extra):
    return {"card": MACHOKE, "evolved_from": MACHOP, "energy": [FIGHTING] * 4, **extra}


def board(attacker, defender=PONYTA, *, hand0=(), bench1=(RATTATA,), turn=TURN):
    return build_test_state([
        {"active": attacker, "bench": [RATTATA], "hand": list(hand0)},
        {"active": defender, "bench": list(bench1)},
    ], turn_number=turn)


def damage_events(state, start):
    return [(e["player"], e["amount"], e.get("target")) for e in state.log[start:] if e["kind"] == "damage"]


class RegistrationTest(unittest.TestCase):
    """登録は、照合した kyuura の写しの文面（照合用）・最新の説明（p.190・p.192）・出典と同じ（M1・M2・M3）。"""

    def test_entries(self):
        karate = DEFAULT_EFFECTS.attack_entry(MACHOKE, 0)
        submission = DEFAULT_EFFECTS.attack_entry(MACHOKE, 1)
        toss = DEFAULT_EFFECTS.attack_entry(MACHAMP, 0)
        low_kick = DEFAULT_EFFECTS.attack_entry(MACHOP, 0)
        self.assertEqual((karate.effect, karate.name_ja, karate.source), (DamageReducedByOwnCounters(reduction_per_counter=10), "からてチョップ", "P43 p.190"))
        self.assertEqual(karate.play_text_ja, "このワザのダメージは、自分にのっているダメージカウンターの数×10だけ、小さくなる。")
        self.assertEqual(karate.text_ja, "自分のダメージカウンター×10だけ、相手にあたえるダメージがへる。")
        self.assertEqual((submission.effect, submission.name_ja, submission.play_text_ja, submission.source),
                         (DamageAndSelfDamage(self_damage=20), "じごくぐるま", "自分にも20ダメージ。", "P43 p.190"))
        self.assertIsInstance(toss.effect, DamageOnly)
        self.assertEqual(toss.name_ja, "ちきゅうなげ")
        self.assertIsInstance(low_kick.effect, DamageOnly)
        pool = load_card_pool()
        for card in (MACHOP, MACHOKE, MACHAMP):
            self.assertTrue(pool.is_playable(card))
            for attack in pool.get(card).attacks:
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, attack), (card, attack.name_ja))

    def test_verification_records(self):
        records = read_verification()["cards"]
        self.assertEqual((records[MACHOKE]["page"], records[MACHOKE]["pdf_page"]), (190, 192))
        self.assertEqual(records[MACHOKE]["latest_description_ja"]["0"], DEFAULT_EFFECTS.attack_entry(MACHOKE, 0).play_text_ja)
        self.assertEqual(records[MACHAMP]["power_latest_description_ja"]["0"], DEFAULT_EFFECTS.power_entry(MACHAMP, 0).play_text_ja)
        self.assertEqual((records[MACHAMP]["page"], records[MACHAMP]["pdf_page"]), (192, 194))
        self.assertIn(GIOVANNIS_MACHAMP, records)

    def test_implementation_checks(self):
        """登録の形の確認（``check``）: からてチョップの実装は「−」のワザだけ、じごくぐるまの実装は説明文のある目安の数字のワザだけ。"""
        pool = load_card_pool()
        karate, submission, toss = pool.get(MACHOKE).attacks[0], pool.get(MACHOKE).attacks[1], pool.get(MACHAMP).attacks[0]
        self.assertEqual(DamageReducedByOwnCounters(10).check(karate), [])
        self.assertTrue(DamageReducedByOwnCounters(10).check(submission))
        self.assertEqual(DamageAndSelfDamage(20).check(submission), [])
        self.assertTrue(DamageAndSelfDamage(20).check(toss))
        self.assertTrue(DamageAndSelfDamage(20).check(karate))
        for bad in (0, 5, -10):
            with self.assertRaises(ValueError):
                DamageReducedByOwnCounters(bad)
            with self.assertRaises(ValueError):
                DamageAndSelfDamage(bad)


class KarateChopTest(unittest.TestCase):
    """からてチョップ（M4〜M7）。"""

    def test_reduced_by_own_counters(self):
        """自分のダメージカウンター 1 個につき 10 小さくなる（基本となるダメージ。p.321 の 1 段階）。"""
        for damage, expected in ((0, 50), (10, 40), (30, 20), (40, 10)):
            with self.subTest(damage=damage):
                state = board(machoke(damage=damage), {"card": PONYTA})
                new = apply_command(state, UseAttack(0, 0))
                self.assertEqual(damage_events(new, len(state.log)), [(1, expected, None)])

    def test_zero_or_less_is_no_damage(self):
        """50 以上のダメージなら 0 以下で、2 段階で計算を終え「ダメージを与えなかった」（p.319・p.321。プラスパワーも計算しない）。"""
        for damage in (50, 70):
            state = board(machoke(damage=damage), hand0=[PLUSPOWER])
            plus = apply_command(state, PlayTrainer(0, uids(state, 0, "hand", PLUSPOWER)[0]))
            new = apply_command(plus, UseAttack(0, 0))
            event = next(e for e in new.log[len(plus.log):] if e["kind"] == "damage")
            self.assertEqual((event["amount"], event.get("stopped_after_step_2")), (0, True))

    def test_weakness_resistance_and_pluspower_after_the_reduction(self):
        """減らした数に、弱点（ピカチュウの闘 ×2）・抵抗力（バタフリーの闘 −30）・プラスパワー（+10）を計算する（p.321）。"""
        cases = (({"card": PIKACHU}, 20, False, 60), ({"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD]}, 20, False, 0),
                 ({"card": PONYTA}, 20, True, 40))
        for defender, damage, pluspower, expected in cases:
            with self.subTest(defender=defender["card"], pluspower=pluspower):
                state = board(machoke(damage=damage), defender, hand0=[PLUSPOWER] if pluspower else [])
                if pluspower:
                    state = apply_command(state, PlayTrainer(0, uids(state, 0, "hand", PLUSPOWER)[0]))
                new = apply_command(state, UseAttack(0, 0))
                self.assertEqual([a for _, a, _ in damage_events(new, len(state.log))], [expected])

    def test_profile(self):
        state = board(machoke(damage=20))
        use = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(MACHOKE, 0))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(MACHOKE, 0).effect.damage_profile(state, use), DamageProfile(opponent=(30,)))


class SubmissionTest(unittest.TestCase):
    """じごくぐるま（M8〜M10）。"""

    def test_damage_then_self_damage(self):
        state = board(machoke())
        new = apply_command(state, UseAttack(0, 1))
        self.assertEqual(damage_events(new, len(state.log)), [(1, 60, None), (0, 20, "self")])
        self.assertEqual(new.players[0].active.damage, 20)
        self.assertEqual(check_invariants(new), [])

    def test_self_damage_with_pluspower_and_defender(self):
        """自分へのダメージもワザによるダメージ: プラスパワーで +10（p.90・p.257）、自分のディフェンダーで −20（p.257）。"""
        state = board(machoke(trainers=[(DEFENDER, TURN + 1)]), hand0=[PLUSPOWER])  # 自分の番（7 番）に使ったディフェンダー
        plus = apply_command(state, PlayTrainer(0, uids(state, 0, "hand", PLUSPOWER)[0]))
        new = apply_command(plus, UseAttack(0, 1))
        self.assertEqual(damage_events(new, len(plus.log)), [(1, 70, None), (0, 10, "self")])

    def test_self_damage_even_if_the_opponent_is_knocked_out(self):
        """相手がきぜつしても、自分へのダメージの要素は処理する（p.309）。自分もきぜつすれば同時のきぜつ（p.324）。"""
        state = board(machoke(damage=60), {"card": PONYTA, "damage": 30})
        new = apply_command(state, UseAttack(0, 1))
        self.assertEqual([e.get("simultaneous") for e in new.log[len(state.log):] if e["kind"] == "knock_out"], [True, True])

    def test_profile(self):
        state = board(machoke())
        use = AttackUse(0, state.players[0].active.pokemon_id, AttackKey(MACHOKE, 1))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(MACHOKE, 1).effect.damage_profile(state, use), DamageProfile(opponent=(60,), self_damage=(20,)))


class EvolutionTest(unittest.TestCase):
    """ワンリキー → ゴーリキー → カイリキー（p.310。M11・M12）。サカキのカイリキーはゴーリキーから進化できない（名前が違う）。"""

    def test_chain(self):
        state = build_test_state([
            {"active": {"card": MACHOP, "played_turn": 1}, "bench": [RATTATA], "hand": [MACHOKE, MACHAMP, GIOVANNIS_MACHAMP]},
            {"active": PONYTA},
        ], turn_number=5)
        target = state.players[0].active.pokemon_id
        once = apply_command(state, EvolvePokemon(0, uids(state, 0, "hand", MACHOKE)[0], target))
        with self.assertRaises(IllegalActionError):
            apply_command(once, EvolvePokemon(0, uids(once, 0, "hand", MACHAMP)[0], target))  # 同じ番に 2 回は進化できない
        self.assertEqual(once.cards[once.players[0].active.card].card_id, MACHOKE)
        later = build_test_state([
            {"active": {"card": MACHOKE, "evolved_from": MACHOP}, "bench": [RATTATA], "hand": [MACHAMP, GIOVANNIS_MACHAMP]},
            {"active": PONYTA},
        ], turn_number=7)
        pid = later.players[0].active.pokemon_id
        with self.assertRaises(Exception):
            apply_command(later, EvolvePokemon(0, uids(later, 0, "hand", GIOVANNIS_MACHAMP)[0], pid))
        done = apply_command(later, EvolvePokemon(0, uids(later, 0, "hand", MACHAMP)[0], pid))
        self.assertEqual(done.cards[done.players[0].active.card].card_id, MACHAMP)
        self.assertEqual(done.players[0].active.pokemon_id, pid)
        self.assertEqual(check_invariants(done), [])


if __name__ == "__main__":
    unittest.main()
