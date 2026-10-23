"""v0.17b: R団のカビゴン（PMCG6-073。p.245）の［わるいねぞう］と「たおれこむ」。docs/rocket-snorlax-v0.17b.md（Z1〜Z30）。

- ［わるいねぞう］: 「このカードが「ねむり」状態で、相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを
  与えたポケモンに、20ダメージ。」（最新の説明）。はんげき（v0.10）と同じ窓・同じ処理（特殊能力のダメージ。p.245 の解説「このダメージは特殊能力に
  よるダメージなので「ディフェンダー」ではふせげません」）で、特殊状態の条件だけが違う（ねむりのときだけ）。効果の定義の特殊状態の条件を一般化した
  （``catalog.EffectDefinition.requires``）。
- 「たおれこむ」: 「ダメージを与えた後、自分を「ねむり」状態にする。」。既存の要素 ``Status`` に対象（自分）と「ダメージを与えた後」を加えた。
  ダメージを与えなかったときは原典で決まらない（Z23）ので宣言の前に止める（``UNRESOLVED_EFFECT_AFTER_NO_DAMAGE``）。

根拠のページ: p.245（最新の説明・解説）・p.89（「ダメージを受けたとき」の効果の時点）・p.138（同じ形の特殊能力のダメージ）・p.155（同じ文面の
「たおれこむ」型のワザの解説）・p.159（「とうめい」と特殊能力のダメージ・自分のワザ）・p.309・p.311・p.319〜p.325。kyuura の記録 id: PMCG6-073・
PMCG6-023（NEO-2000-OFFICIAL-RULES）。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pickle
import unittest
from collections import Counter
from types import MappingProxyType

from kyuura_engine import (
    EndTurn, EnergyType, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    check_invariants, new_game, state_to_dict, working_counterattack_power,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import CardPool, load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.conditions import SLEEP
from kyuura_engine.decisions import FORCED_SWITCH
from kyuura_engine.resolution import catalog as C
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs
from kyuura_engine.rng import copy_rng, rng_fingerprint
from kyuura_engine.state import PreventDamage
from tests.helpers import (
    CARD_DATA_COMMIT_SINCE_V0_69,
    with_card_data_commit_before_v0_69,
    ABRA, ALAKAZAM, BILL, BUTTERFREE, CATERPIE, DARK_WARTORTLE, DEFENDER, DODUO, FIGHTING, FIRE, GASTLY, GIOVANNIS_MEOWTH, GRASS,
    GRIMER, H, HAUNTER, KADABRA, KOGAS_MUK, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PLUSPOWER, POTION, PSYCHIC,
    RATTATA, ROCKET_SQUIRTLE, ROCKETS_MOLTRES, ROCKETS_SNORLAX, SWITCH, T, apply_kernel, build_test_state, coin_events, expand_decklist,
    with_coin_results,
    self_sleep_for_other_text,  # v0.87
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_confusion_games import TERMINAL
from tests.test_dark_wartortle_games_v0_13 import WARTORTLE_DECK
from tests.test_haunter_games_v0_9 import card_id, gas_on
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.test_moltres_games_v0_12 import MOLTRES_DECK_A, MOLTRES_DECK_B
from tests.v017_games import full, play_game

TURN = 7  # プレイヤー 0 の番
RESTLESS = E.PowerKey(ROCKETS_SNORLAX, 0)
TUMBLE = E.AttackKey(ROCKETS_SNORLAX, 0)
DOUBLE_KO = "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"
NO_DAMAGE = "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"


def snorlax(**extra):
    return {"card": ROCKETS_SNORLAX, "energy": [FIRE] * 3, **extra}


def machop(**extra):
    return {"card": MACHOP, "energy": [FIGHTING], **extra}  # けたぐり 20（闘。R団のカビゴンの弱点で 40）


def machamp(**extra):
    return {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "energy": [FIGHTING] * 4, **extra}


def board(mine, theirs, *, mine_bench=None, theirs_bench=None, turn=TURN, **kwargs):
    return build_test_state([
        {"active": mine, "bench": list(mine_bench) if mine_bench is not None else [RATTATA]},
        {"active": theirs, "bench": list(theirs_bench) if theirs_bench is not None else [RATTATA]},
    ], turn_number=turn, **kwargs)


def kinds(state, since):
    return [e["kind"] for e in state.log[since:] if e["kind"] not in ("turn_end", "pokemon_check", "turn_start", "draw")]


def events(state, since, kind):
    return [dict(e) for e in state.log[since:] if e["kind"] == kind]


def snapshot(state):
    return state_to_dict(state, format_version=9), rng_fingerprint(state.rng), len(state.log)


class RegistrationTest(unittest.TestCase):
    def test_card_and_registration(self):
        """登録・照合の記録（p.245）・要素の並び（既存の要素。v0.13 の約束のアダプタでない）・効果の定義（ねむりのときだけ）。"""
        pool = load_card_pool()
        definition = pool.get(ROCKETS_SNORLAX)
        self.assertTrue(definition.supported and pool.is_playable(ROCKETS_SNORLAX))
        power = E.DEFAULT_EFFECTS.power_entry(RESTLESS.card_id, RESTLESS.power_index)
        self.assertEqual(power.effect, E.CounterattackDamageWhileAsleep(amount=20))
        self.assertFalse(power.effect.declared)  # Z4
        self.assertEqual(power.source, "P43 p.245")
        record = read_verification()["cards"][ROCKETS_SNORLAX]
        self.assertEqual(power.play_text_ja, record["power_latest_description_ja"]["0"])
        attack = E.DEFAULT_EFFECTS.attack_entry(TUMBLE.card_id, TUMBLE.attack_index)
        self.assertIs(type(attack.effect), E.DamageAndSelfSleep)
        self.assertEqual((attack.play_text_ja, attack.source), (record["latest_description_ja"], "P43 p.245"))
        program = programs.compile_attack(attack.effect)
        self.assertEqual(program, (programs.Damage(programs.OPP, programs.Printed()),
                                   programs.Status(SLEEP, target=programs.SELF, after_damage="damage")))
        self.assertFalse(contract.is_contract(contract.program_for(attack.effect)))
        self.assertEqual(programs.opponent_effect_elements(program), ())  # 自分への効果（G37 の対象外）
        self.assertIs(E.DamageAndSelfSleep.resolve, E.AttackEffect.resolve)
        self.assertIs(C.definition_for(power.effect, C.POWER_DEFINITIONS), C.RESTLESS_SLEEP)
        self.assertEqual((C.RESTLESS_SLEEP.requires, C.RESTLESS_SLEEP.disabled_by, C.RESTLESS_SLEEP.action),
                         (frozenset({"sleep"}), frozenset(), C.STRIKES_BACK.action))

    def test_kogas_muk_is_rejected_without_the_power_registration(self):
        """キョウのベトベトンは、だつりょくえきを実装していない登録表では未対応（効果のないものとして扱わない。v0.17c）。v0.68 でだつりょくえきを採用の仕様で登録したので、
        同梱の登録表では対応（tests/test_final_pmcg_cards_v0_68.py）。"""
        registry = E.DEFAULT_EFFECTS.without_powers("test-no-energy-drain", [E.PowerKey(KOGAS_MUK, 0)])
        definition = pool_from_extract(read_extract(), registry).get(KOGAS_MUK)
        self.assertFalse(definition.supported)
        self.assertTrue(any("だつりょくえき" in reason for reason in definition.unsupported_reasons))
        self.assertTrue(load_card_pool().is_playable(KOGAS_MUK))

    def test_power_is_not_declarable(self):
        """宣言しない特殊能力（Z4）。使おうとしても状態・乱数・ログは変わらない。"""
        state = board(snorlax(), RATTATA)
        before = snapshot(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_NOT_DECLARABLE")
        self.assertEqual(snapshot(state), before)

    def test_catalog_and_implementation_agree(self):
        """効果の定義の特殊状態の条件（catalog の requires・disabled_by）と、実装の works_with（v0.13 の部品・ログの監査が使う）が、どの特殊状態
        でも同じ答え（はんげき・わるいねぞう）。どくは関係しない（Z3）。"""
        cases = [{}, {"sleep": True}, {"paralysis": 6}, {"confusion": True}, {"poison": 10}, {"sleep": True, "poison": 10},
                 {"confusion": True, "poison": 10}]
        for spec, card in ((snorlax, ROCKETS_SNORLAX), (machamp, MACHAMP)):
            for extra in cases:
                with self.subTest(card=card, conditions=extra):
                    state = board(RATTATA, spec(**extra))
                    holder = state.players[1].active
                    (instance,) = [i for i in C.instances(state, 1, holder) if i.definition.action == "power_damage_to_damage_source"]
                    self.assertEqual(C.working(state, instance, holder), instance.implementation.is_working(holder))
                    expected = (extra.get("sleep", False) if card == ROCKETS_SNORLAX
                                else not any(k in extra for k in ("sleep", "paralysis", "confusion")))
                    self.assertEqual(C.working(state, instance, holder), expected)
                    self.assertEqual(working_counterattack_power(state, holder.pokemon_id) is not None, expected)


class RestlessSleepTest(unittest.TestCase):
    """［わるいねぞう］（Z1〜Z20）。プレイヤー 0 が、プレイヤー 1 の R団のカビゴンにワザを使う。"""

    def attack(self, attacker, defender, index=0, coins=(), **kwargs):
        state = board(attacker, defender, **kwargs)
        new = apply_command(with_coin_results(state, *coins) if coins else state, UseAttack(0, index))
        self.assertEqual(check_invariants(new), [])
        return state, new

    def test_asleep_snorlax_returns_20(self):
        """ねむりのカビゴンが相手のワザのダメージを受けたら、ダメージを与えたポケモンに 20（Z1・Z2・Z6）。ダメージ → 20 の順。"""
        state, new = self.attack(machop(), snorlax(sleep=True))
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "counterattack"])
        (counter,) = events(new, len(state.log), "counterattack")
        self.assertEqual((counter["power"], counter["amount"], counter["attacker_pokemon_id"]), (str(RESTLESS), 20, state.players[0].active.pokemon_id))
        self.assertEqual(new.players[0].active.damage, 20)

    def test_only_while_asleep(self):
        """ねむりでないとき（何もなし・マヒ・こんらん）は、はたらかない（Z2・Z3）。どくはねむりといっしょなら、はたらく。"""
        for extra, works in (({}, False), ({"paralysis": 6}, False), ({"confusion": True}, False), ({"poison": 10}, False),
                             ({"sleep": True, "poison": 10}, True)):
            with self.subTest(conditions=extra):
                state, new = self.attack(machop(), snorlax(**extra))
                self.assertEqual(len(events(new, len(state.log), "counterattack")), 1 if works else 0)

    def test_knocked_out_snorlax_still_returns(self):
        """ワザのダメージでカビゴンがきぜつしても与える（Z5）。"""
        state, new = self.attack(machop(), snorlax(sleep=True, damage=60))
        self.assertEqual(kinds(new, len(state.log))[:4], ["attack", "damage", "counterattack", "knock_out"])
        self.assertEqual(new.players[0].active.damage, 20)

    def test_zero_or_prevented_damage_does_not_trigger(self):
        """最終ダメージが 0（ケーシィのねんりき 10 − 抵抗力 30）・「ダメージを受けない」状態ではダメージを受けていないので、はたらかない（Z17）。
        「ダメージを受けない」状態の R団のカビゴンは自然な対戦では起こらない（盤面を直接作った）。"""
        state, new = self.attack({"card": ABRA, "energy": [PSYCHIC]}, snorlax(sleep=True), coins=(T,))
        self.assertEqual(events(new, len(state.log), "damage")[0]["amount"], 0)
        self.assertEqual(events(new, len(state.log), "counterattack"), [])
        state, new = self.attack(machop(), snorlax(sleep=True, prevent_damage=TURN - 1))
        self.assertEqual((events(new, len(state.log), "counterattack"), new.players[1].active.damage), ([], 0))

    def test_defender_does_not_reduce_the_20(self):
        """ワザを使ったポケモンについているディフェンダーは、特殊能力のダメージを減らさない（p.245「「ディフェンダー」ではふせげません」。Z7）。
        R団のカビゴンについているディフェンダーはワザのダメージを減らすが、0 より大きければはたらく。"""
        state, new = self.attack(machop(trainers=[(DEFENDER, TURN + 1)]), snorlax(sleep=True))
        self.assertEqual(new.players[0].active.damage, 20)
        state, new = self.attack(machop(), snorlax(sleep=True, trainers=[(DEFENDER, TURN)]))
        self.assertEqual((events(new, len(state.log), "damage")[0]["amount"], len(events(new, len(state.log), "counterattack"))), (20, 1))

    def test_power_damage_is_not_evaluated_by_transparency(self):
        """特殊能力のダメージは「とうめい」で防げない（p.159「特殊能力によるダメージや効果は受けます」・T30・Z8）。対応カードでは、「とうめい」を持つ
        ゴーストのワザ（あくむ 10。超）は R団のカビゴンの抵抗力（超 −30）で 0 になり［わるいねぞう］ははたらかない（起こらない）ので、カビゴンの
        抵抗力を外したテスト専用のカードの組で確かめる: あくむの 10 → 20 はゴーストに（「とうめい」のコインなし）。"""
        pool = load_card_pool()
        definitions = dict(pool.definitions)
        definitions[ROCKETS_SNORLAX] = dataclasses.replace(definitions[ROCKETS_SNORLAX], resistance=None, resistance_value=0)
        test_pool = CardPool(MappingProxyType(definitions), pool.playable_ids, pool.source, pool.effects)
        haunter = {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        state, new = self.attack(haunter, snorlax(sleep=True), turn=TURN + 2, pool=test_pool)
        self.assertEqual([e for e in events(new, len(state.log), "evade_check") if e["pokemon_id"] == state.players[0].active.pokemon_id], [])
        self.assertEqual(new.players[0].active.damage, 20)

    def test_no_chain_with_counterattack(self):
        """カイリキーのちきゅうなげでカビゴンがきぜつ → 20 はカイリキーに。特殊能力のダメージなので、カイリキーの「はんげき」ははたらかない（Z10）。"""
        state, new = self.attack(machamp(), snorlax(sleep=True), turn=TURN + 4)
        self.assertEqual(len(events(new, len(state.log), "counterattack")), 1)
        self.assertEqual(new.players[0].active.damage, 20)

    def test_chemical_gas(self):
        """どちらの場のベトベトンのかがくへんかガスでも消える（Z14。G4）。"""
        muk = {"card": MUK, "evolved_from": GRIMER}
        for mine, theirs in (([muk], [RATTATA]), ([RATTATA], [muk])):
            with self.subTest(gas="attacker" if mine[0] is muk else "holder"):
                state, new = self.attack(machop(), snorlax(sleep=True), mine_bench=mine, theirs_bench=theirs)
                self.assertEqual(events(new, len(state.log), "counterattack"), [])

    def test_attacker_already_knocked_out_by_its_own_damage(self):
        """ピカチュウのでんげきが「うら」で自分にも 10 → ピカチュウがすでに HP 以上なら 20 は与えない（counterattack_skipped。Z11）。「おもて」なら
        20 でピカチュウだけがきぜつ（カビゴンはきぜつしないので C18 ではない）。"""
        pikachu = {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING], "damage": 30}
        state, new = self.attack(pikachu, snorlax(sleep=True), index=1, coins=(T,))
        self.assertEqual(len(events(new, len(state.log), "counterattack_skipped")), 1)
        state, new = self.attack(pikachu, snorlax(sleep=True), index=1, coins=(H,))
        self.assertEqual(events(new, len(state.log), "counterattack")[0]["knocked_out"], True)

    def test_drain_and_forced_switch_after_the_20(self):
        """メガドレインのバタフリーが 20 できぜつしたら回復しない（drain_heal_skipped。Z12）。ふきとばしは 20 のあとで入れ替える（p.89）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS] * 4, "damage": 50}
        state, new = self.attack(butterfree, snorlax(sleep=True), index=1, turn=TURN + 4)
        self.assertEqual(len(events(new, len(state.log), "drain_heal_skipped")), 1)
        state, new = self.attack({**butterfree, "damage": 0}, snorlax(sleep=True), index=0, turn=TURN + 4)
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "counterattack"])
        self.assertEqual(new.decision.kind, FORCED_SWITCH)
        bench = new.decision.options[0]
        switched = apply_command(new, ResolveDecision(1, new.decision.id, (bench,)))
        moved = next(pk for pk in switched.players[1].bench if card_id(switched, pk) == ROCKETS_SNORLAX)
        self.assertFalse(moved.conditions.asleep)  # ベンチにもどったら特殊状態は消える（p.322）

    def test_non_attack_damage_does_not_trigger(self):
        """ポケモンチェックのどく（p.321「「どく」のダメージは、「ワザによるダメージ」としてはあつかわれません」）・ダメージスワップ（ダメージを受けた
        ことにならない。p.320）では、はたらかない（Z16）。"""
        state = board(RATTATA, snorlax(sleep=True, poison=10))
        new = apply_command(state, EndTurn(0))
        self.assertIn("poison_damage", kinds(new, len(state.log)))
        self.assertEqual(events(new, len(state.log), "counterattack"), [])
        alakazam = {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "damage": 20}
        state = board(snorlax(sleep=True), RATTATA, mine_bench=[alakazam])
        holder, alakazam_pid = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
        new = apply_command(state, UsePokemonPower(0, alakazam_pid, 0, source=alakazam_pid, target=holder))
        self.assertEqual((new.players[0].active.damage, events(new, len(state.log), "counterattack")), (10, []))

    def test_double_knock_out_stops_before_the_attack(self):
        """カビゴンがワザのダメージで、ワザを使ったポケモンが 20 で、そろってきぜつしうるなら C18 と同じ問い（Z13。新しいコードにしない）で宣言の
        前に止める。理由の文は「わるいねぞう」と p.245。隣の止まらない場合: カビゴンがねむりでない・ワザを使ったポケモンが 20 で HP 未満。"""
        state = board(machop(damage=30), snorlax(sleep=True, damage=60))
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, DOUBLE_KO)
        self.assertIn("「わるいねぞう」の 20 ダメージ", ctx.exception.message)
        self.assertIn("p.245", ctx.exception.message)
        self.assertEqual(snapshot(state), before)
        for attacker, defender in ((machop(damage=30), snorlax(damage=60)), (machop(damage=20), snorlax(sleep=True, damage=60))):
            new = apply_command(board(attacker, defender), UseAttack(0, 0))
            self.assertEqual(check_invariants(new), [])

    def test_counterattack_message_is_unchanged(self):
        """はんげき（v0.10）の C18 の理由の文は v0.16 と同じ（「はんげき」・p.192）。"""
        error = E.counterattack_double_knockout_error(2, 10, 1)
        self.assertIn("その「はんげき」の 10 ダメージで", error.message)
        self.assertIn("（p.89・p.192・p.311・p.323〜p.325）", error.message)

    def test_weakness_resistance_guard(self):
        """Z9: 説明に「弱点・抵抗力」に関係なく、がない特殊能力のダメージで、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプ（無色）なら、
        計算するかで結果が変わるので止める。今の対応カード（kyuura の記録の 780 枚）に無色の弱点・抵抗力はないので、カードの定義を書きかえた
        テスト専用のカードの組で確かめる（v0.17〜v0.60 はコードのない問いで RuntimeError。v0.61 で［ファイナルビーム］（説明に弱点・抵抗力がなく、
        受けるポケモンの弱点「水」で起こる）のために停止コード UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE を付けた。docs/reactive-powers-trainer-damage-v0.61.md）。"""
        pool = load_card_pool()
        definitions = dict(pool.definitions)
        definitions[MACHOP] = dataclasses.replace(definitions[MACHOP], weakness=EnergyType.COLORLESS)
        test_pool = CardPool(MappingProxyType(definitions), pool.playable_ids, pool.source, pool.effects)
        state = board(machop(), snorlax(sleep=True), pool=test_pool)
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")
        self.assertEqual(snapshot(state), before)
        # はんげき（説明に「弱点・抵抗力」に関係なく、がある）は止めない
        state = board(machop(), machamp(), pool=test_pool)
        self.assertEqual(check_invariants(apply_command(state, UseAttack(0, 0))), [])

    def test_no_colorless_weakness_or_resistance_in_the_data(self):
        """Z9 の前提: 写しのカードに、無色の弱点・抵抗力を持つカードはない（わるいねぞうの 20 に弱点・抵抗力を計算するかで結果が変わらない）。"""
        for record in read_extract()["cards"]:
            pokemon = record.get("pokemon") or {}
            for entry in (pokemon.get("weaknesses") or []) + (pokemon.get("resistances") or []):
                self.assertNotEqual(entry["type"], "colorless", record["id"])


class TumbleTest(unittest.TestCase):
    """「たおれこむ」（Z21〜Z29）。プレイヤー 0 の R団のカビゴンがワザを使う。"""

    def test_damage_then_self_sleep(self):
        """相手に 20 → 自分をねむり（Z21）。そのあとのポケモンチェックで、ねむりのコインを投げる。"""
        state = board(snorlax(), MACHOP)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:3], ["attack", "damage", "special_condition"])
        condition = events(new, len(state.log), "special_condition")[0]
        self.assertEqual((condition["player"], condition["condition"], condition["effect"]), (0, "sleep", str(TUMBLE)))
        self.assertTrue(new.players[0].active.conditions.asleep)
        self.assertEqual(events(new, len(state.log), "sleep_check")[0]["player"], 0)

    def test_knocking_out_the_defender_still_sleeps(self):
        """相手をきぜつさせても（ダメージを与えた）、自分はねむりになる（Z24）。"""
        state = board(snorlax(), {"card": MACHOP, "damage": 40})
        new = apply_command(state, UseAttack(0, 0))
        order = kinds(new, len(state.log))
        self.assertLess(order.index("special_condition"), order.index("knock_out"))

    def test_conditions_of_snorlax(self):
        """こんらんの「おもて」ならねむりに置きかわり、「うら」なら 20 で効果なし（Z25）。どくはそのまま（Z26）。ねむり・マヒでは宣言できない（Z28）。"""
        state = board(snorlax(confusion=True), MACHOP)
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertTrue(new.players[0].active.conditions.asleep)
        new = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual((new.players[0].active.conditions.confused, new.players[0].active.damage), (True, 20))
        new = apply_command(with_coin_results(board(snorlax(poison=10), MACHOP), T), UseAttack(0, 0))  # ポケモンチェックのねむりのコインは「うら」
        conditions = new.players[0].active.conditions
        self.assertEqual((conditions.asleep, conditions.poison is not None), (True, True))
        for extra, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED")):
            with self.assertRaises(IllegalActionError) as ctx:
                apply_command(board(snorlax(**extra), MACHOP), UseAttack(0, 0))
            self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(board({"card": ROCKETS_SNORLAX, "energy": [FIRE, FIRE]}, MACHOP), UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_ENERGY")

    def test_counterattack_comes_before_self_sleep(self):
        """カイリキーに 20 → はんげきの 10 → 自分をねむり（p.89・Z21）。はんげきで自分が HP 以上ならねむりにしない（Z22）。そろってきぜつしうるなら
        C18。"""
        state = board(snorlax(), machamp(), turn=TURN + 4)
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:4], ["attack", "damage", "counterattack", "special_condition"])
        state = board(snorlax(damage=80), machamp(), turn=TURN + 4)
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(events(new, len(state.log), "special_condition"), [])
        self.assertIn("knock_out", kinds(new, len(state.log)))
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(board(snorlax(damage=80), machamp(damage=80), turn=TURN + 4), UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, DOUBLE_KO)

    def test_retaliation_comes_before_self_sleep(self):
        """ほのおのかべ（前の番に R団のファイヤーが使った）の 10 → 自分をねむり。カビゴンはまだねむりでないので、わるいねぞうははたらかない（Z21）。
        こうらがえしも同じ。そろってきぜつしうるなら W24・S37（新しいコードにしない）。"""
        state = board(snorlax(), {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1})
        new = apply_command(state, UseAttack(0, 0))
        self.assertEqual(kinds(new, len(state.log))[:5], ["attack", "damage", "retaliation", "damage", "special_condition"])
        self.assertEqual(events(new, len(state.log), "counterattack"), [])
        wartortle = {"card": DARK_WARTORTLE, "evolved_from": ROCKET_SQUIRTLE, "evolved_turn": 4, "retaliation_received": TURN - 1}
        new = apply_command(with_coin_results(board(snorlax(), wartortle), T), UseAttack(0, 0))
        self.assertEqual(new.players[0].active.damage, 20)
        self.assertTrue(new.players[0].active.conditions.asleep)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(board(snorlax(damage=80), {"card": ROCKETS_MOLTRES, "retaliation": TURN - 1, "damage": 40}), UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT")

    def test_no_damage_stops_before_the_attack(self):
        """ディフェンダーで 0・「ダメージを受けない」状態（かたまる）・「とうめい」で受けない、のどれかになりうると、自分をねむりにするかが決まらない
        （Z23）ので、宣言の前に止める。プラスパワーで 10 を与えるなら止めない。"""
        for target in ({"card": MACHOP, "trainers": [(DEFENDER, TURN)]}, {"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": TURN - 1},
                       {"card": HAUNTER, "evolved_from": GASTLY}):
            with self.subTest(target=target["card"]):
                state = board(snorlax(), target)
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, 0))
                self.assertEqual(ctx.exception.code, NO_DAMAGE)
                self.assertEqual(snapshot(state), before)
        new = apply_command(with_coin_results(board(snorlax(trainers=[(PLUSPOWER, TURN)]), {"card": MACHOP, "trainers": [(DEFENDER, TURN)]}), T),
                            UseAttack(0, 0))
        self.assertEqual((events(new, 0, "damage")[-1]["amount"], new.players[0].active.conditions.asleep), (10, True))

    def test_no_damage_stops_in_every_preflight_mode(self):
        """v0.17d: 宣言の前の先読みの方法（derived・derived_full・比べる方法 legacy）のどれでも、「とうめい」のコインの結果によらず Z23 で止める
        （状態は変わらない）。legacy は v0.13 の止める関数で確かめた型（``v013_checks.VERIFIED``）だけにそれを使い、たおれこむ（VERIFIED に
        ない）はすべての結果を試す方法で確かめる。v0.13 の止める関数は Z23 を知らないので、使うと「うら」のときだけ受け付けてしまう
        （docs/card-extensibility-verification-v0.17d.md 6 章）。"""
        for mode in PREFLIGHT_MODES:
            for side in (H, T):
                with self.subTest(mode=mode, coin=side):
                    state = with_coin_results(board(snorlax(), {"card": HAUNTER, "evolved_from": GASTLY}), side)
                    before = snapshot(state)
                    with self.assertRaises(UnsupportedError) as ctx:
                        apply_kernel(state, UseAttack(0, 0), preflight=mode)
                    self.assertEqual(ctx.exception.code, NO_DAMAGE)
                    self.assertEqual(snapshot(state), before)

    def test_both_actives_asleep_halts_the_pokemon_check(self):
        """相手の対戦ポケモンもねむりなら、ポケモンチェックのねむりのコインの順番が決まらない（既存の UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER。Z29）。"""
        new = apply_command(board(snorlax(), {"card": MACHOP, "sleep": True}), UseAttack(0, 0))
        self.assertEqual((new.phase, new.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"))

    def test_self_effect_is_evaluated_by_transparency(self):
        """自分への効果も、効果を与える直前に「とうめい」を評価する（T8。自分のワザでもはたらく）。R団のカビゴンは「とうめい」を持たないので、
        テスト専用の登録表で、ゴーストの「あくむ」（10。説明は相手をねむり）を DamageAndSelfSleep として処理して確かめる（ゴースト側のコイン 1 枚）。"""
        haunter = load_card_pool().get(HAUNTER)
        attack = haunter.attacks[0]
        registry = E.DEFAULT_EFFECTS.with_attacks("test-self-sleep", {
            E.AttackKey(HAUNTER, 0): E.AttackEntry(self_sleep_for_other_text(), attack.name_ja, text_ja=attack.text_ja, play_text_ja="（テスト）", source="test"),
        })
        pool = pool_from_extract(read_extract(), registry)
        for side, asleep in ((H, False), (T, True)):
            state = board({"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}, MACHOP, turn=TURN + 2, effects=registry, pool=pool)
            new = apply_command(with_coin_results(state, side, T), UseAttack(0, 0))  # 2 枚目はポケモンチェックのねむりのコイン（「うら」）
            checks = events(new, len(state.log), "evade_check")
            self.assertEqual([(e["player"], e["element"]) for e in checks], [(0, "sleep")])
            self.assertEqual(new.players[0].active.conditions.asleep, asleep)


# ---------------------------------------------------------------- 正式な開始（new_game）からの対戦

SNORLAX_DECK = expand_decklist({
    ROCKETS_SNORLAX: 4, GIOVANNIS_MEOWTH: 3, RATTATA: 3, DODUO: 3, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2, FIRE: 35,
})
SEEDS = tuple(range(80))
HALTED = {27: "UNRESOLVED_MULLIGAN_COMPENSATION"}  # 対戦準備の既存の未解決の裁定（v0.1 から。R団のカビゴンとは関係しない）
# たおれこむで自分をねむりにし、相手の番に［わるいねぞう］がはたらいた（20 でワザを使ったポケモンがきぜつ）対戦（v0.17b）
GOLDEN_SEED = 4
GOLDEN = (151, 46, Phase.GAME_OVER, "d2a4cb4068cb0710de4098897f0293b1e253d6252823e0552ffe6cee8c0990d6")


def decks(seed):
    """seed を 4 で割った余りで相手（炎・いろいろなワザ（はんげき・とうめい・かがくへんかガス・ふきとばし・メガドレイン・ディフェンダー…）・
    わるいカメール）、2 で割った余りで席を決める。"""
    opponent = (MOLTRES_DECK_A, MOLTRES_DECK_B, MOLTRES_DECK_B, WARTORTLE_DECK)[seed % 4]
    return (SNORLAX_DECK, opponent) if seed % 2 == 0 else (opponent, SNORLAX_DECK)


def no_damage_possible(state, command):
    """Z23 で止まるのが正しいか（エンジンの関数を使わない）: R団のカビゴンのたおれこむで、相手にディフェンダー（プラスパワーがなければ 0）・今の番に
    はたらく「ダメージを受けない」状態・はたらいている「とうめい」のどれかがある。"""
    me, target = state.players[command.player].active, state.players[1 - command.player].active
    if card_id(state, me) != ROCKETS_SNORLAX:
        return False
    defender = any(state.cards[t.card].card_id == DEFENDER for t in target.trainers)
    plus = any(state.cards[t.card].card_id == PLUSPOWER for t in me.trainers)
    prevented = any(isinstance(e, PreventDamage) and e.active_turn == state.turn_number for e in target.persistent_effects)
    return (defender and not plus) or prevented or evasion_working(state, target)


def restless_working(state, pokemon):
    """［わるいねぞう］がはたらいているか（エンジンの関数を使わない。p.245・p.48）。"""
    return card_id(state, pokemon) == ROCKETS_SNORLAX and pokemon.conditions.asleep and not gas_on(state)


def count(state):
    counted = Counter()
    for e in state.log:
        if e["kind"] == "counterattack" and e["power"] == str(RESTLESS):
            counted["restless_sleep"] += 1
            counted["restless_sleep_knock_out"] += e["knocked_out"]
        elif e["kind"] == "counterattack_skipped" and e["power"] == str(RESTLESS):
            counted["restless_sleep_skipped"] += 1
        elif e["kind"] == "special_condition" and e.get("effect") == str(TUMBLE):
            counted["tumble_self_sleep"] += 1
        elif e["kind"] == "sleep_check":
            counted["sleep_check"] += 1
    counted[f"phase_{state.phase.value}"] += 1
    return counted


def play(seed):
    return play_game(decks(seed), seed, cure=seed % 3 != 0, not_declarable=(ROCKETS_SNORLAX,), extra_stop={NO_DAMAGE: no_damage_possible},
                     double_ko_check=lambda s, t: counter_working(s, t) or restless_working(s, t))


class NaturalGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play(seed) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(observed)
            counted.update(count(state))
        return counted

    def test_counts(self):
        """自然な対戦の中で、たおれこむで自分をねむりにし、相手の番に［わるいねぞう］がはたらき（きぜつしても）、たおれこむが Z23 で止まり、ねむりの
        カビゴンはワザを宣言できない（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in (f"attack_{TUMBLE}", "tumble_self_sleep", "restless_sleep", "restless_sleep_knock_out", f"stopped_attack_{NO_DAMAGE}",
                    "rejected_attack_POKEMON_ASLEEP", "sleep_check"):
            self.assertGreater(counted[key], 0, (key, dict(counted)))
        halted = {seed: state.halt.code for seed, (state, _, _) in self.games.items() if state.phase is Phase.HALTED}
        self.assertEqual(halted, HALTED)
        self.assertEqual(counted["phase_game_over"], len(SEEDS) - len(HALTED))

    def test_invariants_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（［わるいねぞう］の時点・量・ねむりの条件を、ログから組み立てた特殊状態で確かめる）・書き出しの監査に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay_and_save_restore(self):
        """同じ seed・同じ操作の列で同じ結果。ねむりの R団のカビゴンがいる状態で保存（pickle）して再開しても同じ。"""
        restored = 0
        for seed, (state, commands, _) in self.games.items():
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                if any(restless_working(replayed, p.active) for p in replayed.players if p.active is not None):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreater(restored, 0)


class GoldenGameTest(unittest.TestCase):
    """GOLDEN_SEED の対戦の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.17b）。手順・デッキ・乱数の使い方が変わると変わる。"""

    def test_seed(self):
        state, commands, _ = play(GOLDEN_SEED)
        counted = count(state)
        self.assertTrue(counted["tumble_self_sleep"] > 0 and counted["restless_sleep_knock_out"] > 0, dict(counted))
        data = full(state)
        # v0.69: 写しの元を上げた（7d3f4ca）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT_SINCE_V0_69)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual((len(commands), state.turn_number, state.phase, digest), GOLDEN)


if __name__ == "__main__":
    unittest.main()
