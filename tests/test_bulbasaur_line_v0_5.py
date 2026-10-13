"""フシギダネ（PMCG1-001）・フシギソウ（PMCG1-008）・フシギバナのワザ（v0.5）と、フシギダネ → フシギソウ → フシギバナの進化。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。

- p.13（フシギダネ）: やどりぎのタネ（草草）20。最新の説明「相手にダメージを与えたら、自分にのっているダメージカウンターを1個
  とりのぞく。」（印刷の文面は「…とりのぞくことができる」。最新の説明にしたがい、選ばずにとりのぞく）。解説「このワザはダメージを
  与えないと、自分のダメージカウンターを取れないので、相手のポケモンが「ディフェンダー」などを使ってダメージを与えられなかった場合は、
  ダメージカウンターを取りのぞくことができません」
- p.14（フシギソウ）: つるのむち（草無無）30（説明文なし。kyuura は「つるのムチ」）、どくのこな（草草草）20「相手を「どく」状態に
  する。」。解説「確実に対戦ポケモンをどく状態にする「どくのこな」」（コインを投げない。コクーンの「どくのこな」（p.21）とは別のワザ）
- p.16（フシギバナ）: ソーラービーム（草草草草）60（説明文なし）
- p.319: 与えたダメージは最終ダメージ。0 以下なら与えなかった。p.320: ダメージカウンターはのっている数より多くはとりのぞかない
- p.321: 「ダメージを受けない」状態でも、ダメージ以外の効果（どく状態）は受ける。p.309・p.323: きぜつした相手への効果は処理しない
- p.322: どくはほかの特殊状態と重なる。どく状態は積み重ならない
- p.310・p.313・p.319: 進化の条件、2 進化ポケモンは 3 枚のカード、きぜつしたらすべてトラッシュしてサイドは 1 枚

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない。
"""

import unittest

from kyuura_engine import (
    EndTurn, EvolvePokemon, PlayTrainer, ResolveDecision, UseAttack, apply_command, check_invariants,
)
from kyuura_engine.cards import load_card_pool, read_verification
from kyuura_engine.effects import DEFAULT_EFFECTS, DamageAndRemoveCounters, PoisonOnHeads, PoisonOpponent
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    BULBASAUR, CATERPIE, DEFENDER, DIGLETT, FIRE, GRASS, GROWLITHE, HITMONCHAN, IVYSAUR, KAKUNA, METAPOD, PLUSPOWER, RATTATA, T,
    VENUSAUR, build_test_state, with_coin_results,
)
from tests.test_pokemon_powers_v0_5 import ivysaur, kinds, run, uid_of, venusaur

LEECH_SEED_PRINTED = "相手にダメージをあたえることができたら、その時点で自分のダメージカウンターを1つとりのぞくことができる。"
LEECH_SEED_LATEST = "相手にダメージを与えたら、自分にのっているダメージカウンターを1個とりのぞく。"
POISONPOWDER = "相手を「どく」状態にする。"
LEECH_SEED, VINE_WHIP, POISON_POWDER, SOLARBEAM = 0, 0, 1, 0


def bulbasaur(**extra):
    return {"card": BULBASAUR, "energy": [GRASS, GRASS], **extra}


def board(mine=None, *, opponent=None, opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=7, current_player=0):
    return build_test_state([
        {"active": mine or bulbasaur(), "bench": [RATTATA], "hand": list(hand)},
        {"active": opponent or HITMONCHAN, "bench": list(opponent_bench), "hand": list(opponent_hand)},
    ], current_player=current_player, turn_number=turn)


def defended(mine, opponent=HITMONCHAN):
    """6 番にプレイヤー 1 が対戦ポケモンにディフェンダーをつけ、7 番（プレイヤー 0 の番）を返す（つけるのは正式なコマンド）。"""
    state = board(mine, opponent=opponent, opponent_hand=(DEFENDER,), turn=6, current_player=1)
    state = apply_command(state, PlayTrainer(1, state.players[1].hand[0]))
    state = apply_command(state, ResolveDecision(1, state.decision.id, (state.players[1].active.pokemon_id,)))
    return apply_command(state, EndTurn(1))


def hardened(mine):
    """相手の対戦ポケモンが、前の番（6 番。相手の番）に「かたまる」で「ダメージを受けない」状態になっている（盤面を直接作った）。"""
    return board(mine, opponent={"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 6})


def events_of(events, kind):
    return [e for e in events if e["kind"] == kind]


class CardTest(unittest.TestCase):
    def test_card_values_and_registrations(self):
        """p.13・p.14 で照合した値と、登録した実装・照合した説明文（kyuura の写し）・最新の説明・出典。"""
        pool = load_card_pool()
        bulba, ivy = pool.get(BULBASAUR), pool.get(IVYSAUR)
        self.assertTrue(pool.is_playable(BULBASAUR) and pool.is_playable(IVYSAUR))
        self.assertEqual((bulba.hp, bulba.pokemon_type.value, bulba.weakness.value, bulba.resistance, bulba.retreat_cost, bulba.powers),
                         (40, "grass", "fire", None, 1, ()))
        self.assertEqual((ivy.hp, ivy.evolves_from, ivy.pokemon_type.value, ivy.weakness.value, ivy.retreat_cost, ivy.powers),
                         (60, "フシギダネ", "grass", "fire", 1, ()))
        self.assertTrue(bulba.is_basic_pokemon and ivy.is_stage1_pokemon)
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.text_ja) for a in bulba.attacks],
                         [("やどりぎのタネ", ["grass", "grass"], 20, LEECH_SEED_PRINTED)])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.text_ja) for a in ivy.attacks],
                         [("つるのムチ", ["grass", "colorless", "colorless"], 30, None), ("どくのこな", ["grass"] * 3, 20, POISONPOWDER)])
        leech = DEFAULT_EFFECTS.attack_entry(BULBASAUR, LEECH_SEED)
        self.assertEqual((leech.effect, leech.text_ja, leech.play_text_ja, leech.source),
                         (DamageAndRemoveCounters(counters=1), LEECH_SEED_PRINTED, LEECH_SEED_LATEST, "P43 p.13"))
        powder = DEFAULT_EFFECTS.attack_entry(IVYSAUR, POISON_POWDER)
        self.assertEqual((powder.effect, powder.play_text_ja, powder.source), (PoisonOpponent(), POISONPOWDER, "P43 p.14"))
        self.assertNotIsInstance(powder.effect, PoisonOnHeads)  # コインを投げる PoisonOnHeads を流用していない
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(IVYSAUR, VINE_WHIP).effect.implementation_id, "damage_only")
        records = read_verification()["cards"]
        self.assertEqual((records[BULBASAUR]["page"], records[BULBASAUR]["latest_description_ja"]), (13, LEECH_SEED_LATEST))
        self.assertEqual((records[IVYSAUR]["page"], records[IVYSAUR]["latest_description_ja"]), (14, POISONPOWDER))
        # ワザ名の表記の違い（kyuura「つるのムチ」、この本「つるのむち」）を記録している
        self.assertEqual(records[IVYSAUR]["mismatches"][0]["official_book_2000"][:5], "つるのむち")


# ---------------------------------------------------------------- やどりぎのタネ


class LeechSeedTest(unittest.TestCase):
    def test_removes_one_counter_after_dealing_damage(self):
        """相手に 20 を与えたら、自分にのっているダメージカウンターを 1 個とりのぞく（与えた量によらず 1 個）。乱数は使わない。"""
        state = board(bulbasaur(damage=30))
        new, events = run(state, UseAttack(0, LEECH_SEED))
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "drain_heal"])
        heal = events_of(events, "drain_heal")[0]
        self.assertEqual({k: heal[k] for k in ("dealt", "drain_counters", "counters", "amount", "damage_before", "total_damage", "effect")},
                         {"dealt": 20, "drain_counters": 1, "counters": 1, "amount": 10, "damage_before": 30, "total_damage": 20,
                          "effect": "PMCG1-001#0"})
        self.assertEqual(new.players[1].active.damage, 20)
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))

    def test_no_counters_to_remove(self):
        """ダメージカウンターがのっていなければ 0 個（ログは残す。のっている数より多くはとりのぞかない。p.320）。"""
        new, events = run(board(), UseAttack(0, LEECH_SEED))
        heal = events_of(events, "drain_heal")[0]
        self.assertEqual((heal["drain_counters"], heal["counters"], heal["amount"], heal["total_damage"]), (1, 0, 0, 0))
        self.assertEqual(new.players[0].active.damage, 0)

    def test_weakness_and_pluspower_do_not_change_the_count(self):
        """弱点（ディグダ。草 ×2 で 40）・プラスパワー（+10 で 30）で与えた量が変わっても、とりのぞくのは 1 個。相手がきぜつしても
        とりのぞく（対象は自分。p.309）。"""
        for name, state, dealt in (
            ("弱点", board(bulbasaur(damage=20), opponent=DIGLETT), 40),
            ("プラスパワー", board(bulbasaur(damage=20), hand=[PLUSPOWER]), 30),
        ):
            with self.subTest(name=name):
                if name == "プラスパワー":
                    state = apply_command(state, PlayTrainer(0, uid_of(state, 0, PLUSPOWER)))
                new, events = run(state, UseAttack(0, LEECH_SEED))
                heal = events_of(events, "drain_heal")[0]
                self.assertEqual((heal["dealt"], heal["counters"]), (dealt, 1))
                self.assertEqual(new.players[0].active.damage, 10)
                if name == "弱点":
                    self.assertEqual(len(events_of(events, "knock_out")), 1)

    def test_no_damage_dealt_no_removal(self):
        """ダメージを与えなかったら（ディフェンダーで最終ダメージ 0・「ダメージを受けない」状態）、とりのぞかない（p.13 の解説・
        p.319・p.321。ログ drain_heal もない）。"""
        for name, state in (("ディフェンダー", defended(bulbasaur(damage=20))), ("かたまる", hardened(bulbasaur(damage=20)))):
            with self.subTest(name=name):
                new, events = run(state, UseAttack(0, LEECH_SEED))
                self.assertEqual(events_of(events, "drain_heal"), [])
                self.assertEqual(new.players[0].active.damage, 20)
                if name == "ディフェンダー":
                    self.assertEqual(events_of(events, "damage")[0]["amount"], 0)
                else:
                    self.assertEqual(len(events_of(events, "damage_prevented")), 1)

    def test_confused_tails_does_not_remove(self):
        """こんらんで「うら」なら、ワザの効果は処理しない（とりのぞかない。v0.3c）。"""
        state = with_coin_results(board(bulbasaur(damage=10, confusion=True)), T)
        new, events = run(state, UseAttack(0, LEECH_SEED))
        self.assertEqual(events_of(events, "drain_heal"), [])
        self.assertEqual(new.players[0].active.damage, 30)  # こんらんの 20（弱点・抵抗力だけ）


# ---------------------------------------------------------------- どくのこな・つるのむち・ソーラービーム


class PoisonpowderTest(unittest.TestCase):
    def test_poisons_without_a_coin(self):
        """20 ダメージのあと、コインを投げずに相手の対戦ポケモンをどく状態にする（乱数を使わない。ログに coin_flip がない）。"""
        state = board(ivysaur(energy=[GRASS] * 3))
        new, events = run(state, UseAttack(0, POISON_POWDER))
        self.assertEqual(kinds(events)[:3], ["attack", "damage", "special_condition"])
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
        self.assertEqual(events_of(events, "damage")[0]["amount"], 20)
        condition = events_of(events, "special_condition")[0]
        self.assertEqual((condition["condition"], condition["effect"], condition.get("already")), ("poison", "PMCG1-008#1", None))
        self.assertIsNotNone(new.players[1].active.conditions.poison)

    def test_poison_is_an_effect_not_damage(self):
        """最終ダメージが 0（ディフェンダー）でも、「ダメージを受けない」状態（かたまる）でも、どく状態にする（p.321「（ダメージ
        以外の効果は受ける）」）。"""
        for name, state in (("ディフェンダー", defended(ivysaur(energy=[GRASS] * 3))), ("かたまる", hardened(ivysaur(energy=[GRASS] * 3)))):
            with self.subTest(name=name):
                new, events = run(state, UseAttack(0, POISON_POWDER))
                self.assertIsNotNone(new.players[1].active.conditions.poison)
                if name == "ディフェンダー":
                    self.assertEqual(events_of(events, "damage")[0]["amount"], 0)
                else:
                    self.assertEqual((events_of(events, "damage"), len(events_of(events, "damage_prevented"))), ([], 1))
                # ワザのダメージはなく、番の終わりのポケモンチェックでどくの 10 だけ（どくのダメージはワザによるダメージではない。p.321）
                self.assertEqual([e["amount"] for e in events_of(events, "poison_damage")], [10])
                self.assertEqual(new.players[1].active.damage, 10)

    def test_already_poisoned_and_other_conditions(self):
        """もうどく状態なら二重にはならない（already）。ねむり・こんらんのポケモンはそのまま重なる（p.322）。"""
        for conditions in ({"poison": 10}, {"sleep": True}, {"confusion": True}, {"poison": 10, "paralysis": 6}):
            with self.subTest(conditions=conditions):
                state = board(ivysaur(energy=[GRASS] * 3), opponent={"card": HITMONCHAN, **conditions})
                new, events = run(state, UseAttack(0, POISON_POWDER))
                condition = events_of(events, "special_condition")[0]
                self.assertEqual(condition.get("already"), True if "poison" in conditions else None)
                names = set(new.players[1].active.conditions.names())
                self.assertIn("poison", names)
                self.assertEqual(check_invariants(new), [])

    def test_knocked_out_defender_is_not_poisoned(self):
        """相手の対戦ポケモンがこのワザのダメージできぜつしたら、どく状態にしない（p.309・p.323）。"""
        new, events = run(board(ivysaur(energy=[GRASS] * 3), opponent=DIGLETT), UseAttack(0, POISON_POWDER))
        self.assertEqual(events_of(events, "special_condition"), [])
        self.assertEqual(len(events_of(events, "knock_out")), 1)

    def test_kakuna_poisonpowder_still_uses_a_coin(self):
        """コクーンの「どくのこな」（p.21）は、同じ名前でもコインを投げるワザ（v0.4b のまま）。"""
        self.assertIsInstance(DEFAULT_EFFECTS.attack_entry(KAKUNA, 1).effect, PoisonOnHeads)


class DamageOnlyAttacksTest(unittest.TestCase):
    def test_vine_whip_and_solarbeam(self):
        """つるのむち（草 1 + 無色 2。炎エネルギーでも払える）30、ソーラービーム（草 4）60。説明文のないワザ。"""
        for name, mine, index, damage in (
            ("つるのむち", ivysaur(energy=[GRASS, FIRE, FIRE]), VINE_WHIP, 30),
            ("ソーラービーム", venusaur(energy=[GRASS] * 4), SOLARBEAM, 60),
        ):
            with self.subTest(name=name):
                new, events = run(board(mine, opponent={"card": RATTATA, "energy": []}, opponent_bench=(HITMONCHAN,)), UseAttack(0, index))
                self.assertEqual(events_of(events, "damage")[0]["amount"], damage)
                self.assertEqual([e["kind"] for e in events if e["kind"] in ("special_condition", "drain_heal", "coin_flip")], [])


# ---------------------------------------------------------------- 進化


class EvolutionLineTest(unittest.TestCase):
    def test_bulbasaur_to_ivysaur_to_venusaur(self):
        """フシギダネ（3 番より前から場にいる）→ 3 番にフシギソウ → 5 番にフシギバナ（正式なコマンド）。ダメージ・エネルギーは
        受け継ぎ、HP・ワザ・特殊能力はいちばん上のカードのもの。きぜつしたら 3 枚すべてトラッシュし、サイドは 1 枚（p.310・p.313）。"""
        state = build_test_state([
            {"active": bulbasaur(damage=10), "bench": [RATTATA], "hand": [IVYSAUR, VENUSAUR], "deck": [GRASS] * 6},
            {"active": {"card": GROWLITHE, "energy": [FIRE, FIRE]}, "bench": [RATTATA], "deck": [FIRE] * 6},
        ], turn_number=3)
        b = state.players[0].active
        state = apply_command(state, EvolvePokemon(0, uid_of(state, 0, IVYSAUR), b.pokemon_id))
        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        state = apply_command(state, EvolvePokemon(0, uid_of(state, 0, VENUSAUR), b.pokemon_id))
        v = state.players[0].active
        self.assertEqual((v.pokemon_id, v.damage, v.energy, len(v.evolution_stack)), (b.pokemon_id, 10, b.energy, 2))
        self.assertEqual([state.cards[u].card_id for u in v.cards()], [BULBASAUR, IVYSAUR, VENUSAUR])
        self.assertEqual(state.card_def(v.card).hp, 100)
        self.assertEqual([e["to_card_id"] for e in state.log if e["kind"] == "evolve"], [IVYSAUR, VENUSAUR])
        self.assertEqual(check_invariants(state), [])
        # きぜつ: 90 ダメージをのせた盤面で相手のガーディ（20 ×2 = 40）
        state.players[0].active.damage = 90
        state = apply_command(state, EndTurn(0))
        state = apply_command(state, UseAttack(1, 0))
        knock = [e for e in state.log if e["kind"] == "knock_out"]
        self.assertEqual(len(knock), 1)
        self.assertTrue(all(u in state.players[0].discard for u in (*knock[0]["evolution_stack"], knock[0]["pokemon"], *b.energy)))
        self.assertEqual(sum(e["kind"] == "take_prize" for e in state.log) + (1 if state.decision else 0), 1)


if __name__ == "__main__":
    unittest.main()
