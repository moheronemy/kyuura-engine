"""v0.61: ワザ・にげる・残りHPではたらく特殊能力とトレーナーのダメージの 4 枚（docs/reactive-powers-trainer-damage-v0.61.md）。

4 枚: わるいギャラドス（PMCG4-025。［ファイナルビーム］・れいとうビーム）・わるいダグトリオ（PMCG4-043。［おとしあな］・つきおとす）・タケシのオコリザル（PMCG5-051。
［ずらかる］・おおあばれ）・バトル場は穴だらけ!（PMCG4-055）。どれも kyuura データの採用（採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合
（わるいギャラドスは読点、バトル場は穴だらけ!はサイトの「抵抗カ」の表記の違いだけ）。ガイドブックは読んでいない。

新しい停止コード: SH1（UNRESOLVED_SINKHOLE_TIMING）・SC1（UNRESOLVED_SCRAM_TIMING）・SC2（UNRESOLVED_SCRAM_POWER_RESTORED）・TD1（UNRESOLVED_TRAINER_DAMAGE_REDUCTION）。
停止コードを付けた既存の問い: Z9（UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE）。再利用: C18（［ファイナルビーム］のダメージのきぜつで勝ち負けが変わる）・G40（きぜつするときに使える
特殊能力が 2 つ）・RB1・BZ2・v0.4b の問い（「ダメージを受けない」相手に投げるコイン）。
"""

from __future__ import annotations

import pathlib
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool
from kyuura_engine.decisions import KNOCK_OUT_POWER
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Paralyzed, Phase
from tests.helpers import (
    BROCKS_MANKEY,
    BROCKS_PRIMEAPE,
    CHARMANDER,
    DARK_DUGTRIO,
    DARK_GYARADOS,
    DIGGER,
    ERIKAS_EXEGGCUTE,
    FIGHTING,
    FIRE,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GRASS,
    GRIMER,
    HITMONCHAN,
    KAKUNA,
    MACHAMP,
    MACHOKE,
    MACHOP,
    MUK,
    PSYCHIC,
    RAINBOW_ENERGY,
    RATTATA,
    ROCKET_DIGLETT,
    ROCKET_MAGIKARP,
    SWITCH,
    V0_61_CARDS,
    WATER,
    WEEDLE,
    CoinSide,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "reactive-powers-trainer-damage-v0.61.md"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, W, G = FIGHTING, WATER, GRASS
TURN = 7


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def gyarados(energy=(W, W, W), **extra):
    return mon(DARK_GYARADOS, energy, evolved_from=ROCKET_MAGIKARP, **extra)


def dugtrio(energy=(F, F), **extra):
    return mon(DARK_DUGTRIO, energy, evolved_from=ROCKET_DIGLETT, **extra)


def primeape(energy=(F, F, F), **extra):
    return mon(BROCKS_PRIMEAPE, energy, evolved_from=BROCKS_MANKEY, **extra)


def table(active, bench=(RATTATA,), *, opponent_active=None, opponent_bench=(RATTATA,), current=0, turn=TURN, hand=(), opponent_hand=(),
          prizes=3, opponent_prizes=3):
    me = {"active": active, "bench": list(bench), "deck": [G] * 10, "prizes": prizes, "hand": list(hand)}
    them = {"active": opponent_active or mon(HITMONCHAN, (F, F, F)), "bench": list(opponent_bench), "deck": [F] * 10, "prizes": opponent_prizes,
            "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def attack(state, index, *coins, player=0, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, UseAttack(player, index), **options)


def answer(state, choices, *coins):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, ResolveDecision(state.decision.player, state.decision.id, tuple(choices)))


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


def card_in(state, player, card_id, zone="hand"):
    return next(uid for uid in getattr(state.players[player], zone) if state.cards[uid].card_id == card_id)


class CardDataTest(unittest.TestCase):
    def test_four_cards_are_supported_and_counted(self):
        pool = load_card_pool()
        for card_id in V0_61_CARDS:
            self.assertTrue(pool.get(card_id).supported, card_id)
            self.assertTrue(pool.is_playable(card_id), card_id)
        # v0.60 の 336・84・10（430）から、ポケモン 3 枚・トレーナー 1 枚を加えた

    def test_registrations(self):
        reg = E.DEFAULT_EFFECTS
        self.assertIsInstance(reg.attack_entry(DARK_GYARADOS, 0).effect, E.ParalyzeOnHeads)
        self.assertEqual(reg.attack_entry(DARK_DUGTRIO, 0).effect, E.OpponentCoinTailsBonusDamage(20))
        self.assertEqual(reg.attack_entry(BROCKS_PRIMEAPE, 0).effect, E.DamageSelfDamageThenDiscardStadium(20))
        beam = reg.power_entry(DARK_GYARADOS, 0).effect
        self.assertIsInstance(beam, E.BeamOnKnockOut)
        self.assertTrue(beam.declared)  # 使用を宣言する任意の特殊能力（「使える」）
        self.assertFalse(reg.power_entry(DARK_DUGTRIO, 0).effect.declared)
        self.assertFalse(reg.power_entry(BROCKS_PRIMEAPE, 0).effect.declared)
        self.assertIsInstance(reg.trainer_entry(DIGGER).effect, E.AlternateCoinsUntilTailsDamage)
        self.assertTrue(reg.trainer_entry(DIGGER).effect.may_knock_out)

    def test_knock_down_is_not_the_bench_coin_type(self):
        """つきおとすは v0.40 の OpponentFlipsTailsDamage（控えの数だけのコイン・「うら」の数 × のダメージ）と別の型（意味が違う）。"""
        pool = load_card_pool()
        knock_down = pool.get(DARK_DUGTRIO).attacks[0]
        self.assertEqual(E.OpponentCoinTailsBonusDamage(20).check(knock_down), [])
        self.assertTrue(E.OpponentFlipsTailsDamage(20).check(knock_down))

    def test_ruling_ids_and_questions(self):
        text = DOC.read_text(encoding="utf-8")
        for ruling, code in (("SH1", "UNRESOLVED_SINKHOLE_TIMING"), ("SC1", "UNRESOLVED_SCRAM_TIMING"), ("SC2", "UNRESOLVED_SCRAM_POWER_RESTORED"),
                             ("TD1", "UNRESOLVED_TRAINER_DAMAGE_REDUCTION"), ("Z9", "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")):
            self.assertIn(ruling, text)
            self.assertIn(code, text)
        self.assertEqual(QUESTIONS["power_damage_weakness_resistance"].code, "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")
        self.assertEqual(QUESTIONS["scram_timing"].code, "UNRESOLVED_SCRAM_TIMING")
        self.assertEqual(QUESTIONS["scram_power_restored"].code, "UNRESOLVED_SCRAM_POWER_RESTORED")


# ---------------------------------------------------------------- ファイナルビーム


class FinalBeamTest(unittest.TestCase):
    """［ファイナルビーム］: 相手のワザによって「きぜつ」する時（ワザのあとのきぜつの判定）に、持ち主が使うかを決める。使うならコイン →「おもて」なら「水」エネルギーの数 × 20 を
    きぜつさせたポケモンに（特殊能力のダメージ）。"""

    def knocked(self, energy=(W, W, W), attacker=None, **gyarados_extra):
        state = table(attacker or mon(RATTATA, (F,)), opponent_active=gyarados(energy, damage=50, **gyarados_extra))
        after = attack(state, 0)  # ラッタの「かみつく」20 → わるいギャラドスの残り HP 0
        return state, after

    def test_offered_when_knocked_out_by_opponents_attack(self):
        _, offered = self.knocked()
        d = offered.decision
        self.assertEqual((d.kind, d.player, d.resume, d.min_choices, d.max_choices), (KNOCK_OUT_POWER, 1, "knock_out", 0, 1))
        self.assertEqual(d.context_value("source"), offered.players[0].active.pokemon_id)
        self.assertIsNone(d.context_value("unresolved_choices", None))
        audited(self, offered)

    def test_decline_flips_no_coin(self):
        _, offered = self.knocked()
        after = answer(offered, ())
        events = since(after, offered)
        self.assertIn("knock_out_power_declined", kinds(events))
        self.assertNotIn("coin_flip", kinds(events))
        self.assertEqual(after.players[0].active.damage, 0)
        self.assertEqual(after.decision.kind, "take_prize")  # 相手がサイドを取る
        audited(self, after)

    def test_heads_deals_water_energy_times_twenty_to_the_knocking_pokemon(self):
        """「水」エネルギーの数（基本エネルギーカード 1 枚 1 個）。ほかの色は数えない。ワザのダメージではない（弱点・抵抗力・プラスパワーなどを当てはめない）。"""
        _, offered = self.knocked(energy=(W, W, F))
        target = offered.players[0].active
        after = answer(offered, (offered.decision.options[0],), H)
        damage = next(e for e in since(after, offered) if e["kind"] == "knock_out_power_damage")
        self.assertEqual((damage["energy"], damage["amount"], damage["target_pokemon_id"]), (2, 40, target.pokemon_id))
        # ラッタ（HP 30）もきぜつ。同じきぜつの処理（どちらもサイドを取る。勝ち負けは決まらないので C18 で止めない）
        knock_outs = [e for e in since(after, offered) if e["kind"] == "knock_out"]
        self.assertEqual({e["player"] for e in knock_outs}, {0, 1})
        audited(self, after)
        # サイドを取る: 番のプレイヤー（ラッタの持ち主ではなく、きぜつさせたほう）から 1 枚ずつ
        first = answer(after, (0,))
        second = answer(first, (0,))
        self.assertEqual((len(second.players[0].prizes), len(second.players[1].prizes)), (2, 2))
        audited(self, second)

    def test_tails_does_nothing(self):
        _, offered = self.knocked()
        after = answer(offered, (offered.decision.options[0],), T)
        events = since(after, offered)
        self.assertEqual(kinds(events)[:3], ["knock_out_power_declared", "coin_flip", "knock_out_power_failed"])
        self.assertEqual(after.players[0].active.damage, 0)

    def test_coin_flipped_once_by_owner(self):
        _, offered = self.knocked()
        after = answer(offered, (offered.decision.options[0],), H)
        coins = [e for e in since(after, offered) if e["kind"] == "coin_flip"]
        self.assertEqual([(c["player"], c["source"]) for c in coins], [(1, "power")])

    def test_not_offered_while_status_at_knock_out(self):
        """「ねむり・マヒ・こんらん」状態のまま「きぜつ」する時は使えない（きぜつの判定の時点の特殊状態）。どくは関係しない。"""
        for status, offered in (({"confusion": True}, False), ({"sleep": True}, False), ({"paralysis": TURN - 1}, False), ({"poison": 10}, True)):
            state = table(mon(RATTATA, (F,)), opponent_active=gyarados(damage=50, **status))
            after = attack(state, 0)
            self.assertEqual(after.decision is not None and after.decision.kind == KNOCK_OUT_POWER, offered, status)

    def test_not_offered_under_chemical_gas_or_goop_gas(self):
        """かがくへんかガス・まきちらせ!ベトベトガスで「使えず」（``catalog.offer_stopped``。こんじょう・ふしちょうと共通の確かめ）。ショックアイを受けたポケモンも同じ確かめで
        止まるが、効果のはたらく間（与えた番と次の相手の番）にわるいギャラドスが相手のワザで「きぜつ」するのは返す効果のダメージだけで、単体の盤面を作れない。"""
        from tests.helpers import GOOP_GAS_ATTACK
        muk = table(mon(RATTATA, (F,)), opponent_active=gyarados(damage=50), opponent_bench=(mon(MUK, (), evolved_from=GRIMER),))
        after = attack(muk, 0)
        self.assertFalse(after.decision is not None and after.decision.kind == KNOCK_OUT_POWER)
        self.assertEqual(after.decision.kind, "take_prize")
        goop = table(mon(RATTATA, (F,)), opponent_active=gyarados(damage=50), hand=(GOOP_GAS_ATTACK,))
        played = apply_kernel(goop, PlayTrainer(0, card_in(goop, 0, GOOP_GAS_ATTACK)))
        after = attack(played, 0)
        self.assertEqual(after.decision.kind, "take_prize")
        plain = attack(table(mon(RATTATA, (F,)), opponent_active=gyarados(damage=50)), 0)
        self.assertEqual(plain.decision.kind, KNOCK_OUT_POWER)

    def test_not_offered_for_non_attack_knock_outs(self):
        """こんらんの自分への 20・トレーナーのダメージ（バトル場は穴だらけ!）では使えない（相手のワザではない）。"""
        confused = table(gyarados(damage=60, confusion=True), opponent_active=mon(RATTATA, (F,)))
        after = attack(confused, 0, T)  # こんらんの「うら」→ 自分に 20 → きぜつ
        self.assertNotEqual(after.decision and after.decision.kind, KNOCK_OUT_POWER)
        digger = table(mon(RATTATA, (G,)), opponent_active=gyarados(damage=60), hand=(DIGGER,))
        after = apply_kernel(with_coin_results(digger, H, T), PlayTrainer(0, card_in(digger, 0, DIGGER)))
        self.assertNotIn("knock_out_power_declared", kinds(after.log))
        self.assertTrue(any(e["kind"] == "knock_out" and e.get("timing") == "trainer" for e in after.log))

    def test_weakness_to_water_stops_only_when_used(self):
        """弱点・抵抗力が説明に書かれていない（Z9）。受けるポケモンの弱点が「水」（ヒトカゲ）なら、使うを選ぶと止める（使わないは選べる）。"""
        state = table(mon(CHARMANDER, (FIRE, FIRE)), opponent_active=gyarados(damage=60))
        offered = attack(state, 0)  # ひっかく 10
        self.assertEqual(offered.decision.context_value("unresolved_code"), "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")
        assert_stops(self, offered, ResolveDecision(1, offered.decision.id, (offered.decision.options[0],)), "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")
        declined = answer(offered, ())
        audited(self, declined)

    def test_rainbow_energy_stops_only_when_used(self):
        state = table(mon(RATTATA, (F,)), opponent_active=gyarados((W, RAINBOW_ENERGY), damage=50))
        offered = attack(state, 0)
        self.assertEqual(offered.decision.context_value("unresolved_code"), "UNRESOLVED_RAINBOW_ENERGY_TYPE")

    def test_double_knock_out_that_decides_the_game_stops(self):
        """［ファイナルビーム］のダメージできぜつさせたポケモンもきぜつし、どちらかがサイドを取り終える（勝ち負けが決まる）なら、同時のきぜつかで勝ち負けが変わる（C18）。"""
        state = table(mon(RATTATA, (F,)), opponent_active=gyarados(damage=50), prizes=1, opponent_prizes=3)
        offered = attack(state, 0)
        self.assertEqual(offered.decision.context_value("unresolved_code"), "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
        declined = answer(offered, ())
        self.assertEqual(declined.decision.kind, "take_prize")

    def test_guts_and_final_beam_in_the_same_check(self):
        """こんじょうと［ファイナルビーム］が同じきぜつの判定で使える（G40 と同じ問い）。ベンチにもダメージを与えるワザで起こる。"""
        from tests.helpers import FOSSIL_ZAPDOS, LIGHTNING
        machamp = mon(GIOVANNIS_MACHAMP, (), evolved_from=[GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], damage=100)
        state = table(mon(FOSSIL_ZAPDOS, (LIGHTNING,) * 4), opponent_active=machamp, opponent_bench=(gyarados(damage=60),))
        assert_stops(self, with_coin_results(state, H), UseAttack(0, 0), "UNRESOLVED_KO_PREVENTION_ORDER")

    def test_destiny_bond_knock_out_stops(self):
        """「みちづれ」でわるいギャラドスも「きぜつ」するとき、それが「相手のワザによって」か（使える機会があるか）は、みちづれのきぜつの扱いの問い（HC2 と同じコード）で、
        わるいギャラドスのワザの宣言の前に止める（v0.60 まではコードのない問いで、［ファイナルビーム］で初めて起こる）。"""
        from tests.helpers import BASE_GASTLY
        state = table(mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)), opponent_active=gyarados(), current=0, turn=TURN)
        bonded = attack(state, 1)  # みちづれ（エネルギーをトラッシュする決定のあと番が終わる）
        while bonded.decision is not None:
            bonded = answer(bonded, (bonded.decision.options[0],))
        self.assertEqual(bonded.current_player, 1)
        assert_stops(self, bonded, UseAttack(1, 0), "UNRESOLVED_DESTINY_BOND_KNOCKOUT")
        self.assertEqual(QUESTIONS["destiny_bond_with_ko_prevention"].code, "UNRESOLVED_DESTINY_BOND_KNOCKOUT")

    def test_save_and_restore_while_waiting(self):
        _, offered = self.knocked()
        restored = pickle.loads(pickle.dumps(offered))
        self.assertEqual(snapshot(restored), snapshot(offered))
        a = answer(offered, (offered.decision.options[0],), H)
        b = answer(restored, (restored.decision.options[0],), H)
        self.assertEqual(snapshot(a), snapshot(b))

    def test_invalid_answer_keeps_the_decision(self):
        _, offered = self.knocked()
        for bad in ((offered.players[0].active.pokemon_id,), (offered.decision.options[0], offered.decision.options[0])):
            before = snapshot(offered)
            with self.assertRaises(IllegalActionError):
                apply_kernel(offered, ResolveDecision(1, offered.decision.id, bad))
            self.assertEqual(snapshot(offered), before)
        with self.assertRaises(IllegalActionError):
            apply_kernel(offered, ResolveDecision(0, offered.decision.id, ()))  # 決めるのは持ち主

    def test_cannot_be_declared_with_use_pokemon_power(self):
        state = table(gyarados())
        with self.assertRaises(IllegalActionError) as caught:
            apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(caught.exception.code, "POWER_NOT_USABLE_NOW")

    def test_ice_beam(self):
        state = table(gyarados(), opponent_active=mon(HITMONCHAN, (F,)))
        heads = attack(state, 0, H)
        tails = attack(state, 0, T)
        self.assertEqual((heads.players[1].active.damage, tails.players[1].active.damage), (30, 30))
        self.assertIsInstance(heads.players[1].active.conditions.exclusive, Paralyzed)
        self.assertIsNone(tails.players[1].active.conditions.exclusive)


# ---------------------------------------------------------------- おとしあな・つきおとす


class SinkholeTest(unittest.TestCase):
    def retreat(self, state, *coins, discard=()):
        if coins:
            state = with_coin_results(state, *coins)
        return apply_kernel(state, Retreat(0, tuple(discard), state.players[0].bench[0].card))

    def test_tails_damages_the_retreated_pokemon_on_the_bench(self):
        state = table(mon(RATTATA, (G,)), opponent_active=dugtrio())
        old = state.players[0].active
        after = self.retreat(state, T)
        events = since(after, state)
        self.assertEqual(kinds(events), ["retreat", "coin_flip", "sinkhole_check", "sinkhole_damage"])
        coin = events[1]
        self.assertEqual((coin["player"], coin["source"]), (0, "power"))  # にげたプレイヤーが投げる
        self.assertEqual(after.players[0].bench[0].pokemon_id, old.pokemon_id)
        self.assertEqual(after.players[0].bench[0].damage, 20)  # 弱点・抵抗力に関係なく 20
        self.assertEqual(after.phase, Phase.MAIN)  # 番は続く
        audited(self, after)

    def test_heads_does_nothing_and_retreat_is_not_prevented(self):
        state = table(mon(RATTATA, (G,)), opponent_active=dugtrio())
        after = self.retreat(state, H)
        self.assertNotIn("sinkhole_damage", kinds(since(after, state)))
        self.assertEqual(after.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id)

    def test_dugtrio_on_the_bench_also_works(self):
        state = table(mon(RATTATA, (G,)), opponent_bench=(dugtrio(),))
        self.assertIn("sinkhole_damage", kinds(since(self.retreat(state, T), state)))

    def test_status_and_gas_on_dugtrio(self):
        asleep = table(mon(RATTATA, (G,)), opponent_active=dugtrio(sleep=True))
        self.assertNotIn("sinkhole_check", kinds(since(self.retreat(asleep), asleep)))
        gas = table(mon(RATTATA, (G,)), opponent_active=dugtrio(), opponent_bench=(mon(MUK, (), evolved_from=GRIMER),))
        self.assertNotIn("sinkhole_check", kinds(since(self.retreat(gas), gas)))

    def test_switch_is_not_retreating(self):
        state = table(mon(RATTATA, (G,)), opponent_active=dugtrio(), hand=(SWITCH,))
        after = apply_kernel(state, PlayTrainer(0, card_in(state, 0, SWITCH)))
        if after.decision is not None:
            after = answer(after, (after.decision.options[0],))
        self.assertNotIn("sinkhole_check", kinds(after.log))

    def test_confused_retreat_stops(self):
        state = table(mon(RATTATA, (G,), confusion=True), opponent_active=dugtrio())
        assert_stops(self, state, Retreat(0, (), state.players[0].bench[0].card), "UNRESOLVED_SINKHOLE_TIMING")

    def test_knock_out_on_the_bench_gives_a_prize_and_continues_the_turn(self):
        state = table(mon(RATTATA, (G,), damage=10), opponent_active=dugtrio())
        after = self.retreat(state, T)
        self.assertEqual(after.decision.kind, "take_prize")
        self.assertEqual(after.decision.player, 1)
        taken = answer(after, (0,))
        self.assertEqual(taken.phase, Phase.MAIN)
        self.assertEqual(taken.current_player, 0)
        self.assertTrue(any(e["kind"] == "knock_out" and e.get("timing") == "retreat" for e in taken.log))
        audited(self, taken)

    def test_two_sinkholes_flip_two_coins(self):
        state = table(mon(RATTATA, (G,)), opponent_active=dugtrio(), opponent_bench=(dugtrio(),))
        after = self.retreat(state, T, H)
        self.assertEqual(kinds(since(after, state)).count("coin_flip"), 2)
        self.assertEqual(after.players[0].bench[0].damage, 20)

    def test_knock_down(self):
        state = table(dugtrio(), opponent_active=mon(HITMONCHAN, (F,)))
        heads = attack(state, 0, H)
        tails = attack(state, 0, T)
        self.assertEqual(heads.players[1].active.damage, 20)
        self.assertEqual(tails.players[1].active.damage, 40)
        coin = next(e for e in tails.log if e["kind"] == "coin_flip")
        self.assertEqual(coin["player"], 1)  # 相手プレイヤーが投げる

    def test_knock_down_against_prevented_damage_stops_before_the_coin(self):
        state = table(dugtrio(), opponent_active=mon(KAKUNA, (), evolved_from=WEEDLE, prevent_damage=TURN - 1))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_PREVENTED_COIN_DAMAGE")


# ---------------------------------------------------------------- ずらかる


class ScramTest(unittest.TestCase):
    def test_mega_thrash_self_damage_to_ten_returns_then_discards_the_stadium(self):
        """自分に 20 → 残りHP「10」→［ずらかる］で山札にもどる → そのあとスタジアムをトラッシュ（このカードが場にいなくても止まらない）。"""
        from tests.helpers import PEWTER_CITY_GYM
        state = table(primeape(damage=40), hand=(PEWTER_CITY_GYM,))
        stadium_card = card_in(state, 0, PEWTER_CITY_GYM)
        placed = apply_kernel(state, PlayTrainer(0, stadium_card))
        self.assertEqual(placed.stadium.card, stadium_card)
        after = attack(placed, 0)
        order = kinds(since(after, placed))
        self.assertLess(order.index("scram"), order.index("stadium_discarded"))
        self.assertIsNone(after.players[0].active)
        self.assertIsNone(after.stadium)
        self.assertEqual(after.decision.kind, "promote_active")
        self.assertIn(stadium_card, after.players[0].discard)  # 持ち主のトラッシュ
        audited(self, after)

    def test_mega_thrash_without_stadium(self):
        state = table(primeape(damage=40))
        after = attack(state, 0)
        events = since(after, state)
        self.assertEqual(kinds(events)[-4:], ["scram", "return_in_play_to_deck", "shuffle", "stadium_discard_none"])
        cards = next(e for e in events if e["kind"] == "return_in_play_to_deck")["cards"]
        self.assertTrue(set(cards) <= set(after.players[0].deck))  # このカードとついているすべてのカード
        self.assertEqual(after.decision.kind, "promote_active")
        audited(self, after)
        promoted = answer(after, (after.decision.options[0],))
        self.assertEqual(promoted.current_player, 1)  # ワザのあとなので番は終わる
        audited(self, promoted)

    def test_only_exactly_ten(self):
        for damage, expected in ((30, False), (40, True), (50, False)):
            state = table(primeape(damage=damage))
            after = attack(state, 0)
            self.assertEqual("scram" in kinds(after.log), expected, damage)

    def test_opponents_attack_to_ten(self):
        state = table(mon(HITMONCHAN, (F, F, F)), opponent_active=primeape(damage=20))
        after = attack(state, 1)  # スペシャルパンチ 40
        self.assertIn("scram", kinds(since(after, state)))
        self.assertEqual(after.decision.kind, "promote_active")
        self.assertEqual(after.decision.player, 1)

    def test_status_keeps_the_power_off(self):
        state = table(mon(HITMONCHAN, (F, F, F)), opponent_active=primeape(damage=20, confusion=True))
        after = attack(state, 1)
        self.assertNotIn("scram", kinds(after.log))
        self.assertEqual(after.players[1].active.damage, 60)

    def test_passing_ten_inside_one_attack_stops(self):
        """残りHPが「10」になってから同じワザのダメージの処理でさらにダメージを受ける（相手のはんげき）と、はたらく時点で結果が変わる（SC1）。"""
        machamp = mon(MACHAMP, (), evolved_from=[MACHOP, MACHOKE])
        state = table(primeape(damage=40), opponent_active=machamp)  # 自分に 20 で「10」→ はんげき 10 で HP 以上
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_SCRAM_TIMING")

    def test_effect_left_on_the_scrammed_defender_stops(self):
        """相手の対戦ポケモンが［ずらかる］でもどったあとに、そのワザの効果の要素（コインでマヒ）が残る（SC1）。"""
        state = table(gyarados(), opponent_active=primeape(damage=30))
        assert_stops(self, state, UseAttack(0, 0), "UNRESOLVED_SCRAM_TIMING")

    def test_poison_to_ten_at_pokemon_check(self):
        state = table(primeape(damage=50, poison=10), current=0)
        after = apply_kernel(state, EndTurn(0))
        events = since(after, state)
        self.assertIn("scram", kinds(events))
        self.assertEqual(after.decision.kind, "promote_active")
        self.assertEqual(after.decision.player, 0)
        promoted = answer(after, (after.decision.options[0],))
        self.assertEqual(promoted.current_player, 1)
        audited(self, promoted)

    def test_waking_up_at_ten_halts(self):
        """残りHPが「10」でねむっていた（力が消えていた）ポケモンの、ねむりのコインの前に止める（SC2）。"""
        state = table(primeape(damage=60, sleep=True), current=0)
        after = apply_kernel(state, EndTurn(0))
        self.assertEqual(after.phase, Phase.HALTED)
        self.assertEqual(after.halt.code, "UNRESOLVED_SCRAM_POWER_RESTORED")

    def test_switch_clears_confusion_at_ten_is_rejected(self):
        state = table(primeape(damage=60, confusion=True), hand=(SWITCH,))
        command = PlayTrainer(0, card_in(state, 0, SWITCH))
        before = snapshot(state)
        try:
            after = apply_kernel(state, command)
        except UnsupportedError as error:
            self.assertEqual(error.code, "UNRESOLVED_SCRAM_POWER_RESTORED")
            self.assertEqual(snapshot(state), before)
            return
        # 入れ替える控えを選ぶ決定のあと
        assert_stops(self, after, ResolveDecision(0, after.decision.id, (after.decision.options[0],)), "UNRESOLVED_SCRAM_POWER_RESTORED")

    def test_retreat_at_ten_with_confusion_is_rejected_before_the_coin(self):
        state = table(primeape((F,), damage=60, confusion=True))
        assert_stops(self, state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card), "UNRESOLVED_SCRAM_POWER_RESTORED")

    def test_sinkhole_to_ten_returns_from_the_bench(self):
        state = table(primeape((F,), damage=40), opponent_active=dugtrio())
        after = apply_kernel(with_coin_results(state, T), Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertIn("scram", kinds(since(after, state)))
        self.assertEqual(len(after.players[0].bench), 0)  # にげてベンチにもどったオコリザルが山札にもどる
        self.assertEqual(after.phase, Phase.MAIN)
        audited(self, after)

    def test_two_sinkholes_passing_ten_stop_before_the_coins(self):
        state = table(primeape((F,), damage=40), opponent_active=dugtrio(), opponent_bench=(dugtrio(),))  # 1 つめで「10」→ 2 つめで HP 以上
        assert_stops(self, state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card), "UNRESOLVED_SCRAM_TIMING")

    def test_final_beam_to_ten(self):
        # おおあばれ 60 − 抵抗力 30 = 30 でわるいギャラドス（ダメージ 40）がきぜつ。自分に 20 で残り 30 →［ファイナルビーム］「水」1 個 × 20 で「10」
        state = table(primeape(damage=20), opponent_active=gyarados((W,), damage=40))
        offered = attack(state, 0)
        self.assertEqual(offered.decision.kind, KNOCK_OUT_POWER)
        after = answer(offered, (offered.decision.options[0],), H)
        events = since(after, offered)
        self.assertLess(kinds(events).index("knock_out_power_damage"), kinds(events).index("scram"))
        audited(self, after)

    def test_digger_to_ten(self):
        state = table(primeape((F,), damage=50), hand=(DIGGER,))
        after = apply_kernel(with_coin_results(state, T), PlayTrainer(0, card_in(state, 0, DIGGER)))
        self.assertIn("scram", kinds(since(after, state)))
        self.assertEqual(after.decision.kind, "promote_active")
        promoted = answer(after, (after.decision.options[0],))
        self.assertEqual((promoted.phase, promoted.current_player), (Phase.MAIN, 0))  # トレーナーのあとは同じ番
        audited(self, promoted)


# ---------------------------------------------------------------- バトル場は穴だらけ!


class DiggerTest(unittest.TestCase):
    def play(self, state, *coins):
        return apply_kernel(with_coin_results(state, *coins), PlayTrainer(0, card_in(state, 0, DIGGER)))

    def test_user_flips_first_and_players_alternate_until_tails(self):
        state = table(mon(RATTATA, (G,)), opponent_active=mon(HITMONCHAN, (F,)), hand=(DIGGER,))
        for coins, loser in (((T,), 0), ((H, T), 1), ((H, H, T), 0), ((H,) * 7 + (T,), 1)):
            after = self.play(state, *coins)
            flips = [e for e in since(after, state) if e["kind"] == "coin_flip"]
            self.assertEqual([f["player"] for f in flips], [i % 2 for i in range(len(coins))])
            result = next(e for e in after.log if e["kind"] == "digger_result")
            self.assertEqual((result["coins"], result["loser"]), (len(coins), loser))
            self.assertEqual(after.players[loser].active.damage, 10)  # 弱点・抵抗力に関係なく 10
            self.assertEqual(after.players[1 - loser].active.damage, 0)
            audited(self, after)

    def test_prevented_damage_is_not_received(self):
        """「ダメージを受けない」状態はトレーナーカードによるダメージも受けない（v0.28 の p.235 のラッキーの解説）。"""
        state = table(mon(RATTATA, (G,)), opponent_active=mon(KAKUNA, (), evolved_from=WEEDLE, prevent_damage=TURN - 1), hand=(DIGGER,))
        after = self.play(state, H, T)
        self.assertIn("trainer_damage_prevented", kinds(after.log))
        self.assertEqual(after.players[1].active.damage, 0)

    def test_reflector_stops_before_any_coin(self):
        """相手の「リフレクター」（受けるダメージを半分）を当てはめるかで量が変わる（TD1）。相手が受ける結果だけが止まる場合も、コインの前に止める。"""
        start = table(mon(RATTATA, (G,)), opponent_active=mon(ERIKAS_EXEGGCUTE, (PSYCHIC,)), current=1, turn=TURN - 1, hand=(DIGGER,))
        reflected = apply_kernel(start, UseAttack(1, 0))  # 相手の番にリフレクター → 番が終わる
        self.assertEqual(reflected.current_player, 0)
        assert_stops(self, reflected, PlayTrainer(0, card_in(reflected, 0, DIGGER)), "UNRESOLVED_TRAINER_DAMAGE_REDUCTION")

    def test_knock_out_gives_a_prize_after_the_card_is_discarded(self):
        state = table(mon(RATTATA, (G,)), opponent_active=mon(RATTATA, (), damage=20), hand=(DIGGER,))
        after = self.play(state, H, T)
        order = kinds(since(after, state))
        self.assertLess(order.index("discard_trainer"), order.index("knock_out"))
        self.assertEqual(after.decision.kind, "take_prize")
        self.assertEqual(after.decision.player, 0)
        taken = answer(after, (0,))
        promoted = answer(taken, (taken.decision.options[0],))
        self.assertEqual((promoted.phase, promoted.current_player), (Phase.MAIN, 0))
        audited(self, promoted)

    def test_last_prize_wins(self):
        state = table(mon(RATTATA, (G,)), opponent_active=mon(RATTATA, (), damage=20), hand=(DIGGER,), prizes=1)
        after = answer(self.play(state, H, T), (0,))
        self.assertEqual(after.phase, Phase.GAME_OVER)
        self.assertEqual(after.result.winner, 0)


if __name__ == "__main__":
    unittest.main()
