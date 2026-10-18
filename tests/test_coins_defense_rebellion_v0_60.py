"""v0.60: 控えへのコイン・ダメージを受けない効果・攻撃するときの特殊能力・相手の効果を受けないダメージの 4 枚（docs/coins-defense-rebellion-v0.60.md）。

4 枚: サンダー（化石の秘密。PMCG3-026。サンダーストーム）・R団のストライク（PMCG5-016。かげぶんしん・こうそくカマ）・カスミのギャラドス（PMCG5-035。［はんこう］・
ハイドロクラッシュ）・タケシのサンドパン（PMCG5-050。スピードスター・とげボール）。どれも kyuura データの採用（採用したデータのコミット ecb2d69）と pcg-search.com の
同じ版のページとの照合（R団のストライクは「これ以降」と「これ以後」、カスミのギャラドスはサイトの「うち」の表記の違いだけ）。ガイドブックは読んでいない。

新しい停止コード: TS1（UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER）。コードのない問い: SS1（speed_star_scope。今の写しでは起こらない）。再利用: AC13（［はんこう］とほかの
手順 4 の効果）・Z23（かげぶんしんで受けなかった「ダメージを与えた後」の効果）・T27・C18 など。
"""

from __future__ import annotations

import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.persistent import tails_damage_guard
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import TailsDamageGuard
from tests.helpers import (
    BROCKS_SANDSHREW,
    BROCKS_SANDSLASH,
    BULBASAUR,
    DEFENDER,
    FIGHTING,
    FOSSIL_ZAPDOS,
    GASTLY,
    GRASS,
    GRIMER,
    HAUNTER,
    HITMONCHAN,
    IVYSAUR,
    LIGHTNING,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MISTYS_GYARADOS,
    MISTYS_MAGIKARP,
    MR_MIME,
    MUK,
    PIKACHU,
    PLUSPOWER,
    RATTATA,
    ROCKETS_SCYTHER,
    SANDSHREW,
    SQUIRTLE,
    V0_60_CARDS,
    WATER,
    CoinSide,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT, observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "coins-defense-rebellion-v0.60.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, W, G, L = FIGHTING, WATER, GRASS, LIGHTNING
TURN = 7


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def zapdos(**extra):
    return mon(FOSSIL_ZAPDOS, (L, L, L, L), **extra)


def gyarados(energy=(W, W, W, W), **extra):
    return mon(MISTYS_GYARADOS, energy, evolved_from=MISTYS_MAGIKARP, **extra)


def sandslash(energy=(F, F), **extra):
    return mon(BROCKS_SANDSLASH, energy, evolved_from=BROCKS_SANDSHREW, **extra)


def machamp(energy=(), **extra):
    return mon(MACHAMP, energy, evolved_from=[MACHOP, MACHOKE], **extra)


def haunter(**extra):
    return mon(HAUNTER, (), evolved_from=GASTLY, **extra)


def table(active, bench=(RATTATA,), *, opponent_active=None, opponent_bench=(RATTATA,), current=0, turn=TURN, deck=(G,) * 10, opponent_deck=(F,) * 10):
    me = {"active": active, "bench": list(bench), "deck": list(deck), "prizes": 3}
    them = {"active": opponent_active or mon(HITMONCHAN, (F, F, F)), "bench": list(opponent_bench), "deck": list(opponent_deck), "prizes": 3}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index, *coins, player=0, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(player, index), **options)


def since(new, old):
    return list(new.log[len(old.log):])


def kinds(events):
    return [e["kind"] for e in events]


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def assert_stops(test, state, command, code, error=UnsupportedError):
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


def damage_events(events, target=None):
    return [e for e in events if e["kind"] == "damage" and (target is None or e.get("target", "opponent_active") == target)]


class CardDataTest(unittest.TestCase):
    def test_four_cards_are_supported_and_counted(self):
        pool = load_card_pool()
        for card_id in V0_60_CARDS:
            self.assertTrue(pool.get(card_id).supported, card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
            self.assertEqual(pool.get(card_id).category, "pokemon")
        counts = {}
        for definition in pool.definitions.values():
            if definition.supported:
                counts[definition.category] = counts.get(definition.category, 0) + 1
        # v0.59 の 332・84・10（426）から、ポケモン 4 枚を加えた
        self.assertEqual((counts["pokemon"], counts["trainer"], counts["energy"]), (339, 85, 10))  # v0.61 でポケモン 3 枚・トレーナー 1 枚を加えた
        self.assertEqual(sum(counts.values()), 434)

    def test_registrations(self):
        reg = E.DEFAULT_EFFECTS
        self.assertEqual(reg.attack_entry(FOSSIL_ZAPDOS, 0).effect, E.DamageThenCoinPerOpponentBench(20, 10))
        self.assertIsInstance(reg.attack_entry(ROCKETS_SCYTHER, 0).effect, E.SelfTailsDamageGuard)
        self.assertIs(reg.attack_entry(ROCKETS_SCYTHER, 1).effect, E.DAMAGE_ONLY)
        self.assertIs(reg.attack_entry(MISTYS_GYARADOS, 0).effect, E.DAMAGE_ONLY)
        self.assertIsInstance(reg.power_entry(MISTYS_GYARADOS, 0).effect, E.FailAndReturnOnAttack)
        self.assertFalse(reg.power_entry(MISTYS_GYARADOS, 0).effect.declared)
        self.assertIsInstance(reg.attack_entry(BROCKS_SANDSLASH, 0).effect, E.DamageIgnoringDefenderEffects)
        self.assertIsInstance(reg.attack_entry(BROCKS_SANDSLASH, 1).effect, E.PoisonOnHeads)
        self.assertIs(reg.attack_entry(ROCKETS_SCYTHER, 0).effect.guard_terms(), TailsDamageGuard)

    def test_text_variants_are_checked(self):
        """型の check は印刷の文面と照らす（似た文面を受け付けない）。"""
        pool = load_card_pool()
        swift = pool.get(BROCKS_SANDSLASH).attacks[0]
        self.assertEqual(E.DamageIgnoringDefenderEffects().check(swift), [])
        self.assertTrue(E.DamageIgnoringDefenderEffects().check(pool.get(BROCKS_SANDSLASH).attacks[1]))
        storm = pool.get(FOSSIL_ZAPDOS).attacks[0]
        self.assertEqual(E.DamageThenCoinPerOpponentBench(20, 10).check(storm), [])
        self.assertTrue(E.DamageThenCoinPerOpponentBench(10, 10).check(storm))

    def test_ruling_ids_and_questions(self):
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in (("TS1", "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER"), ("SS1", "speed_star_scope")):
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        self.assertEqual(QUESTIONS["bench_coin_transparency_order"].code, "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER")
        self.assertIsNone(QUESTIONS["speed_star_scope"].code)  # 今の写しでは起こらない
        self.assertEqual(LATEST_FORMAT, 19)
        self.assertEqual(max(FORMAT_VERSIONS), 19)  # 形式は増やしていない


class ThunderstormTest(unittest.TestCase):
    """サンダーストーム: 相手に 40 → 控えそれぞれにコイン（並びの順。1 匹 1 枚）→「おもて」の控えに弱点・抵抗力に関係なく 20 →「うら」の数 × 10 を自分に。"""

    def test_each_coin_belongs_to_one_bench_pokemon(self):
        state = table(zapdos(), opponent_bench=(RATTATA, SQUIRTLE, RATTATA))
        bench = [p.pokemon_id for p in state.players[1].bench]
        for coins in ((H, T, T), (T, H, H), (H, H, H), (T, T, T)):
            with self.subTest(coins=coins):
                new = attack(state, 0, *coins)
                events = since(new, state)
                result = next(e for e in events if e["kind"] == "bench_coin_results")
                self.assertEqual(result["targets"], tuple(bench))
                self.assertEqual(result["results"], tuple(c.value for c in coins))
                hit = [e["pokemon_id"] for e in damage_events(events, "opponent_bench")]
                self.assertEqual(hit, [pid for pid, c in zip(bench, coins) if c is H])
                # ゼニガメ（弱点 雷）にも 20（弱点・抵抗力に関係なく）
                self.assertTrue(all(e["amount"] == 20 and e.get("ignore_weakness_resistance") for e in damage_events(events, "opponent_bench")))
                tails = sum(c is T for c in coins)
                self_hits = damage_events(events, "self")
                self.assertEqual([e["amount"] for e in self_hits], [10 * tails] if tails else [])
                # 相手の対戦ポケモンへのダメージ → コイン → 控え → 自分の順
                order = [k for k in kinds(events) if k in ("damage", "bench_coin_results")]
                self.assertEqual(order[:2], ["damage", "bench_coin_results"])
                audited(self, new)

    def test_no_bench_means_no_coins_and_no_self_damage(self):
        state = table(zapdos(), opponent_bench=())
        new = attack(state, 0)
        events = since(new, state)
        self.assertEqual([e for e in events if e["kind"] in ("coin_flip", "bench_coin_results")], [])
        self.assertEqual([e["amount"] for e in damage_events(events)], [40])
        audited(self, new)

    def test_bench_coins_are_flipped_even_if_the_active_takes_no_damage(self):
        """相手の対戦ポケモンが「ダメージを受けない」状態（かたまる）でも、控えへのダメージと自分へのダメージは有効な要素なので、コインを投げる。"""
        state = table(zapdos(), opponent_active=mon(HITMONCHAN, (F,), prevent_damage=TURN - 1), opponent_bench=(RATTATA,))
        new = attack(state, 0, H)
        events = since(new, state)
        self.assertIn("damage_prevented", kinds(events))
        self.assertEqual([e["amount"] for e in damage_events(events, "opponent_bench")], [20])
        audited(self, new)

    def test_counterattack_on_the_bench_hits_zapdos_after_its_own_self_damage(self):
        """控えのカイリキーが「おもて」で 20 を受けると［はんげき］の 10 がサンダーに返る（ダメージの処理をすべて終えたあと。p.89）。"""
        state = table(zapdos(), opponent_bench=(machamp(), RATTATA))
        new = attack(state, 0, H, T)
        events = since(new, state)
        self.assertEqual(kinds([e for e in events if e["kind"] in ("damage", "counterattack")]), ["damage", "damage", "damage", "counterattack"])
        self.assertEqual(new.players[0].active.damage, 10 + 10)
        audited(self, new)

    def test_ts1_transparency_before_another_bench_pokemon(self):
        """TS1: 「とうめい」のゴーストのあとに控えがいると、コインの投げ方で乱数の割り当てが変わるので止める。ゴーストが最後なら止めない。"""
        state = table(zapdos(), opponent_bench=(haunter(), RATTATA))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER")
        last = table(zapdos(), opponent_bench=(RATTATA, haunter()))
        new = attack(last, 0, T, H, T)  # 控えのコイン 2 枚 → ゴーストの「とうめい」のコイン
        events = since(new, last)
        self.assertIn("evade_check", kinds(events))
        audited(self, new)

    def test_self_knock_out_and_bench_knock_out_in_the_same_attack(self):
        """自分へのダメージでサンダーがきぜつし、控えもきぜつする。きぜつの処理はワザのあとにまとめて（両方がサイドを取る）。"""
        state = table(zapdos(damage=70), bench=(RATTATA,), opponent_bench=(mon(RATTATA, (), damage=20), RATTATA))
        new = attack(state, 0, H, T)
        knocked = [e for e in since(new, state) if e["kind"] == "knock_out"]
        self.assertEqual(len(knocked), 2)
        audited(self, new)

    def test_preflight_methods_agree(self):
        state = table(zapdos(), opponent_bench=(RATTATA, machamp(), RATTATA, SQUIRTLE, RATTATA))
        for seed_coins in ((H, H, T, H, T), (T, T, T, T, T), (H, T, H, T, H)):
            results = []
            for method in ("derived", "derived_full", "legacy"):
                new = attack(state, 0, *seed_coins, preflight=method)
                results.append(snapshot(new))
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])


class ShadowImagesTest(unittest.TestCase):
    """かげぶんしん: 相手のワザのダメージを受ける時、相手プレイヤーのコインが「うら」ならそのダメージを受けない。受けたら・バトル場をはなれたら消える。"""

    def guarded(self, **opponent):
        state = table(mon(ROCKETS_SCYTHER, (G, G, G)), opponent_active=opponent.pop("opponent_active", mon(HITMONCHAN, (F, F, F))))
        new = attack(state, 0)
        self.assertIsNotNone(tails_damage_guard(new.players[0].active))
        self.assertIn("persistent_effect_added", kinds(since(new, state)))
        audited(self, new)
        return new

    def test_tails_blocks_the_damage_and_heads_removes_the_effect(self):
        state = self.guarded()
        tails = attack(state, 1, T, player=1)  # スペシャルパンチ 40 − 抵抗力 30 = 10
        check = next(e for e in since(tails, state) if e["kind"] == "damage_guard_check")
        self.assertEqual((check["flipped_by"], check["received"], check["amount"]), (1, False, 10))
        self.assertEqual(tails.players[0].active.damage, 0)
        self.assertIsNotNone(tails_damage_guard(tails.players[0].active))
        heads = attack(state, 1, H, player=1)
        self.assertEqual(heads.players[0].active.damage, 10)
        self.assertIsNone(tails_damage_guard(heads.players[0].active))
        removed = [e for e in since(heads, state) if e["kind"] == "persistent_effect_removed"]
        self.assertEqual([e["reason"] for e in removed], ["damaged"])
        audited(self, tails)
        audited(self, heads)

    def test_zero_final_damage_flips_no_coin(self):
        """ジャブ 20 − 抵抗力 30 は 0 で「ダメージを受けなかった」（p.319・p.321）。コインを投げず、効果も消えない。"""
        state = self.guarded()
        new = attack(state, 0, player=1)
        self.assertNotIn("damage_guard_check", kinds(since(new, state)))
        self.assertIsNotNone(tails_damage_guard(new.players[0].active))

    def test_other_effects_still_apply_and_poison_damage_removes_the_effect(self):
        """どくのこな: 「うら」でダメージは受けないが、どくにはなる。ポケモンチェックのどくのダメージ（ワザのダメージではない）を受けたら効果は消える。"""
        state = self.guarded(opponent_active=mon(IVYSAUR, (G, G, G), evolved_from=BULBASAUR))
        new = attack(state, 1, T, player=1)
        scyther = new.players[0].active
        self.assertEqual(scyther.damage, 10)  # どく 10（ポケモンチェック）
        self.assertIsNotNone(scyther.conditions.poison)
        self.assertIsNone(tails_damage_guard(scyther))
        events = since(new, state)
        self.assertLess(kinds(events).index("damage_guard_check"), kinds(events).index("poison_damage"))
        audited(self, new)

    def test_leaving_the_active_spot_removes_the_effect(self):
        state = self.guarded()
        state = apply_kernel(state, EndTurn(1))
        scyther = state.players[0].active
        new = apply_kernel(state, Retreat(0, (scyther.energy[0],), state.players[0].bench[0].card))
        self.assertIsNone(tails_damage_guard(next(p for p in new.players[0].bench if p.pokemon_id == scyther.pokemon_id)))
        self.assertIn("retreat", [e["reason"] for e in since(new, state) if e["kind"] == "persistent_effect_removed"])
        audited(self, new)

    def test_using_it_again_replaces_the_effect(self):
        state = self.guarded()
        again = attack(apply_kernel(state, EndTurn(1)), 0)
        removed = [e["reason"] for e in since(again, state) if e["kind"] == "persistent_effect_removed"]
        self.assertEqual(removed, ["replaced"])
        self.assertEqual(len([e for e in again.players[0].active.persistent_effects if isinstance(e, TailsDamageGuard)]), 1)
        audited(self, again)

    def test_own_self_damage_removes_the_effect(self):
        """自分のワザ・こんらんのダメージもダメージなので、受けたら消える（説明は「相手のワザによる」と限っていない）。コインは相手のワザのときだけ。"""
        state = table(mon(ROCKETS_SCYTHER, (G, G, G), confusion=True), opponent_active=mon(HITMONCHAN, (F, F, F)))
        state = attack(state, 0, H)  # こんらんのコイン「おもて」→ かげぶんしん
        self.assertIsNotNone(tails_damage_guard(state.players[0].active))
        state = apply_kernel(state, EndTurn(1))
        new = attack(state, 1, T)  # こんらんの「うら」→ 自分に 20
        events = since(new, state)
        self.assertNotIn("damage_guard_check", kinds(events))
        self.assertIn("confusion_damage", kinds(events))
        self.assertIsNone(tails_damage_guard(new.players[0].active))
        audited(self, new)

    def test_effect_after_no_damage_stops_with_z23(self):
        """「ダメージを与えた後、…」の効果（R団のカビゴンの「たおれこむ」）は、「うら」でダメージを受けなかった場合を含むので Z23 で宣言の前に止める。"""
        from tests.helpers import ROCKETS_SNORLAX

        state = self.guarded(opponent_active=mon(ROCKETS_SNORLAX, (G, G, G, G)))
        assert_stops(self, state, UseAttack(1, 0), "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE")

    def test_speed_star_ignores_the_guard(self):
        state = table(sandslash(), opponent_active=mon(ROCKETS_SCYTHER, (G,)), current=1, turn=8)
        state = attack(state, 0, player=1)  # かげぶんしん（番は終わる）
        self.assertEqual(state.current_player, 0)
        new = attack(state, 0)
        events = since(new, state)
        self.assertNotIn("damage_guard_check", kinds(events))
        self.assertEqual(new.players[1].active.damage, 20)
        self.assertIsNone(tails_damage_guard(new.players[1].active))
        audited(self, new)


class RebellionTest(unittest.TestCase):
    """［はんこう］: ワザを使う時（手順 4）に持ち主がコイン 2 枚。すべて「うら」ならワザは失敗し、このカードとついているカードを山札にもどして切る。"""

    def test_both_tails_fails_and_returns_the_pokemon_to_the_deck(self):
        state = table(gyarados(trainers=[(PLUSPOWER, TURN)]), bench=(RATTATA,))
        deck = len(state.players[0].deck)
        new = attack(state, 0, T, T)
        events = since(new, state)
        self.assertEqual(kinds(events)[:6], ["attack", "coin_flip", "coin_flip", "rebellion_check", "attack_failed", "return_in_play_to_deck"])
        failed = next(e for e in events if e["kind"] == "attack_failed")
        self.assertEqual((failed["reason"], failed["power"]), ("power", "PMCG5-035@power0"))
        self.assertNotIn("knock_out", kinds(events))
        self.assertNotIn("damage", kinds(events))
        self.assertEqual(len(new.players[0].deck), deck + 2 + 4 + 1)  # ギャラドス・コイキング・エネルギー 4 枚・プラスパワー
        self.assertIn("shuffle", kinds(events))
        self.assertIsNone(new.players[0].active)
        self.assertEqual(new.decision.kind, "promote_active")  # 控えから出す（きぜつではないのでサイドはない）
        self.assertEqual(len(new.players[1].prizes), 3)
        audited(self, new)

    def test_one_heads_lets_the_attack_happen(self):
        state = table(gyarados())
        new = attack(state, 0, H, T)
        events = since(new, state)
        self.assertEqual(next(e for e in events if e["kind"] == "rebellion_check")["failed"], False)
        self.assertIn("damage", kinds(events))

    def test_no_bench_after_failure_loses_the_game(self):
        state = table(gyarados(), bench=())
        new = attack(state, 0, T, T)
        self.assertEqual(new.phase.value, "game_over")
        self.assertEqual(new.result.winner, 1)

    def test_works_while_confused(self):
        """こんらんでもはたらく。失敗しなければ手順 5 のこんらんのコインに進み、失敗したらこんらんのコインは投げない（ポケモンは場にいない）。"""
        state = table(gyarados(confusion=True))
        fail = attack(state, 0, T, T)
        self.assertNotIn("confusion_check", kinds(since(fail, state)))
        passed = attack(state, 0, H, T, T)
        events = since(passed, state)
        self.assertLess(kinds(events).index("rebellion_check"), kinds(events).index("confusion_check"))
        self.assertIn("confusion_damage", kinds(events))
        audited(self, fail)
        audited(self, passed)

    def test_other_step_four_effect_stops_with_ac13(self):
        state = table(gyarados(), opponent_active=mon(SANDSHREW, (F,)), current=1, turn=8)
        state = attack(state, 0, player=1)  # すなかけ（効果は 1 回できえる）
        self.assertEqual(state.current_player, 0)
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_MULTIPLE_ATTACK_CHECKS")

    def test_chemical_gas_suppresses_the_power(self):
        state = table(gyarados(), opponent_active=mon(MUK, (), evolved_from=GRIMER))
        new = attack(state, 0)
        self.assertNotIn("rebellion_check", kinds(since(new, state)))

    def test_not_declarable(self):
        state = table(gyarados())
        assert_stops(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)

    def test_preflight_methods_agree(self):
        state = table(gyarados(confusion=True), bench=(RATTATA,))
        for coins in ((T, T), (H, T, T), (T, H, H)):
            results = [snapshot(attack(state, 0, *coins, preflight=method)) for method in ("derived", "derived_full", "legacy")]
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])


class SpeedStarTest(unittest.TestCase):
    """スピードスター: 相手の持っている弱点・抵抗力・特殊能力・その他の効果の影響を受けない。ワザを使うポケモンの効果は当てはまる。"""

    def test_weakness_and_defender_are_ignored_but_pluspower_applies(self):
        state = table(sandslash(trainers=[(PLUSPOWER, TURN)]), opponent_active=mon(PIKACHU, (), trainers=[(DEFENDER, TURN)]))
        new = attack(state, 0)
        event = damage_events(since(new, state))[0]
        self.assertEqual(event["amount"], 30)  # 20 + プラスパワー 10（弱点 闘 ×2・ディフェンダー −20 は当てはめない）
        self.assertTrue(event["ignore_defender_effects"])
        audited(self, new)

    def test_powers_and_persistent_effects_of_the_defender_are_ignored(self):
        cases = {
            "mysterious_wall": (mon(MR_MIME, ()), 30),  # ［なぞのかべ］（30 以上を 0）はプラスパワーで 30 でも当てはめない
            "prevent_damage": (mon(HITMONCHAN, (F,), prevent_damage=TURN - 1), 30),  # 「ダメージを受けない」状態でも受ける
        }
        for name, (defender, expected) in cases.items():
            with self.subTest(name):
                state = table(sandslash(trainers=[(PLUSPOWER, TURN)]), opponent_active=defender)
                new = attack(state, 0)
                self.assertEqual(new.players[1].active.damage, expected)
                self.assertNotIn("damage_prevented", kinds(since(new, state)))
                audited(self, new)

    def test_transparency_is_ignored(self):
        state = table(sandslash(), opponent_active=haunter())
        new = attack(state, 0)
        self.assertNotIn("evade_check", kinds(since(new, state)))
        self.assertEqual(new.players[1].active.damage, 20)  # 抵抗力 闘 −30 も当てはめない

    def test_counterattack_still_triggers(self):
        state = table(sandslash(), opponent_active=machamp())
        new = attack(state, 0)
        self.assertEqual(new.players[1].active.damage, 20)
        self.assertIn("counterattack", kinds(since(new, state)))
        self.assertEqual(new.players[0].active.damage, 10)

    def test_needle_ball_poisons_on_heads(self):
        state = table(sandslash())
        heads = attack(state, 1, H)
        self.assertIsNotNone(heads.players[1].active.conditions.poison)
        tails = attack(state, 1, T)
        self.assertIsNone(tails.players[1].active.conditions.poison)


if __name__ == "__main__":
    unittest.main()


class InteractionTest(unittest.TestCase):
    """v0.60 の 4 枚と既存の効果の組み合わせ（ショックアイ・まきちらせ!ベトベトガス・ゆびをふる・状態の複製）。"""

    def test_shock_eye_does_not_stop_rebellion(self):
        """ショックアイ（「特殊能力を使うことができない」だけ）は宣言して使う特殊能力の使用を止めるが、［はんこう］は宣言しない（手順 4 の効果として
        はたらく）ので止まらない（v0.59 の CR-CHEMICAL-GAS-USE-VS-POWER の区別）。"""
        from tests.helpers import DARK_ARBOK, ROCKET_EKANS
        from tests.test_instant_trainers_v0_55 import answer

        arbok = mon(DARK_ARBOK, (G, G, G), evolved_from=ROCKET_EKANS)
        state = table(gyarados(), opponent_active=arbok, current=1, turn=8)
        chosen = apply_kernel(state, UseAttack(1, 0))
        target = state.players[0].active.pokemon_id
        locked = answer(chosen, (target,))
        self.assertTrue(any(e["kind"] == "persistent_effect_added" and e["persistent_effect"] == "cannot_use_powers" for e in locked.log))
        self.assertEqual(locked.current_player, 0)
        new = attack(locked, 0, T, T)
        self.assertIn("rebellion_check", kinds(since(new, locked)))
        audited(self, new)

    def test_goop_gas_suppresses_rebellion(self):
        """まきちらせ!ベトベトガス（使った番から次の相手の番の終わりまで、すべての特殊能力が消える）のはたらく間は［はんこう］のコインを投げない。"""
        from tests.helpers import GOOP_GAS_ATTACK
        from tests.test_instant_trainers_v0_55 import use

        me = {"active": gyarados(), "bench": [RATTATA], "deck": [G] * 10, "prizes": 3, "hand": [GOOP_GAS_ATTACK]}
        them = {"active": mon(HITMONCHAN, (F, F, F)), "bench": [RATTATA], "deck": [F] * 10, "prizes": 3}
        state = build_test_state([me, them], turn_number=TURN, current_player=0)
        gassed = use(state, GOOP_GAS_ATTACK)
        new = attack(gassed, 0)
        events = since(new, gassed)
        self.assertNotIn("rebellion_check", kinds(events))
        self.assertIn("damage", kinds(events))
        audited(self, new)

    def test_copied_shadow_images_guards_the_copier(self):
        """ピッピの「ゆびをふる」でかげぶんしんを使うと、効果はワザを使ったピッピ自身に与える（効果を与えたワザは R団のストライクの「かげぶんしん」）。"""
        from tests.helpers import CLEFAIRY
        from tests.test_instant_trainers_v0_55 import answer

        state = table(mon(CLEFAIRY, (W, W, W)), opponent_active=mon(ROCKETS_SCYTHER, (G,)))
        new = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((new.decision.kind, new.decision.options), ("select_attack", (0, 1)))
        new = answer(new, (0,))  # かげぶんしん（R団のストライクのワザの位置 0）
        guard = tails_damage_guard(new.players[0].active)
        self.assertIsNotNone(guard)
        self.assertEqual(guard.source_card, new.players[0].active.card)
        audited(self, new)

    def test_clone_keeps_the_guard_and_replays_the_same_coin(self):
        """状態を複製しても効果と乱数は同じで、同じコマンドで同じ結果になる（保存と復元）。"""
        state = table(mon(ROCKETS_SCYTHER, (G,)), opponent_active=mon(HITMONCHAN, (F, F, F)))
        guarded = apply_kernel(state, UseAttack(0, 0))
        copy = guarded.clone()
        self.assertEqual(snapshot(copy), snapshot(guarded))
        self.assertEqual(state_to_dict(copy, format_version=LATEST_FORMAT), state_to_dict(guarded, format_version=LATEST_FORMAT))
        a = apply_kernel(guarded, UseAttack(1, 1))
        b = apply_kernel(copy, UseAttack(1, 1))
        self.assertEqual(snapshot(a), snapshot(b))
        self.assertTrue(any(e["kind"] == "damage_guard_check" for e in a.log))
        audited(self, a)
