"""R団のファイヤーのワザ「ほのおのかべ」（v0.12。盤面を直接作るテスト）。

最新の説明（『ポケモンカードオフィシャルブック2000』p.82）: 「次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによって
このカードが「きぜつ」しても、）相手に10ダメージを与える。」 解説（p.82）: 「「ほのおのかべ」は、「R団のファイヤー」がワザによるダメージを
受けたとき、そのダメージを与えた相手の対戦ポケモンに10ダメージを与える効果がついています。この10ダメージは、弱点・抵抗力の影響を受けます。」
同じ「相手の番ではたらく効果」のワザ解説（p.89 のわるいカメールの「こうらがえし」）: 与えるタイミングは相手のワザによるダメージの処理の
あと、ダメージ以外の効果の前。効果の対象はワザを使ったポケモン自身、効果の持続は次の相手の番の最後、ベンチにもどると消える。「ふきとばし」・
「スターブーメラン」の例。返すダメージは「ワザによるダメージ」。一般規定: p.320・p.321（「8」ワザによるダメージ・計算の順番）・p.322
（持続する効果: ベンチにもどったら・場をはなれたら消え、復活しない。特殊状態と重複する）・p.324（同時のきぜつ）。kyuura の記録 id: PMCG5-020・
NEO-2000-OFFICIAL-RULES。

裁定（W1〜W25）は docs/rocket-moltres-v0.12.md、持続する効果の仕組みは docs/temporary-attack-effects-v0.12.md。W24（R団のファイヤーと
ワザを使ったポケモンがそろってきぜつ）は原典で決められないので、ワザの宣言の前に止める（tests/test_unresolved_boundaries_v0_4e.py の
``RetaliationDoubleKnockoutBoundaryTest``。ここではコインの結果で受け付けるかが変わらないことを確かめる）。
"""

import copy
import dataclasses
import itertools
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, AttackKey, EndTurn, EngineError, Phase, ResolveDecision, Retreat, TakePrize, UseAttack, UsePokemonPower,
    apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import KO_PREVENTION, POST_KNOCKOUT_POWER
from kyuura_engine.effects import (
    AttackEffect, AttackEntry, DamageAndRetaliation, DamageProfile, OPPONENT_ACTIVE, deal_attack_damage,
)
from kyuura_engine.persistent import retaliation
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import Retaliation
from tests.helpers import (
    ABRA, ALAKAZAM, BUTTERFREE, CATERPIE, DEFENDER, FIGHTING, FIRE, GASTLY, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP,
    GRASS, GRIMER, H, HAUNTER, KADABRA, LIGHTNING, MACHAMP, MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PONYTA,
    PSYCHIC, RATTATA, ROCKETS_MOLTRES, T, WEEDLE, build_test_state, with_coin_results,
)
from tests.log_audit import serialization_problems
from tests.test_effect_preflight_v0_3d import ATTACKS, EVOLVED_FROM, energy_for

FIRE_WALL = AttackKey(ROCKETS_MOLTRES, 0)
LATEST = "次の相手の番、このカードが相手のワザによるダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）相手に10ダメージを与える。"
PRINTED = "次の相手の番、このカードが相手のワザによるダメージを受けた時、(このカードが「きぜつ」するしないにかかわらず)相手にも10ダメージ。"
TURN = 7  # プレイヤー 0 の番（先攻はプレイヤー 0）。プレイヤー 1 の R団のファイヤーが 6 番に「ほのおのかべ」を使った盤面


def full(state):
    return state_to_dict(state, format_version=9)


def kinds(state, start=0):
    return [e["kind"] for e in state.log[start:]]


def board(attacker, *, moltres=None, attacker_bench=(RATTATA,), moltres_bench=(PONYTA,), turn=TURN, effect=True, **kwargs):
    """プレイヤー 0 の ``attacker`` が、前の番に「ほのおのかべ」を使ったプレイヤー 1 の R団のファイヤーを攻撃する盤面。"""
    holder = {"card": ROCKETS_MOLTRES, **({"retaliation": turn - 1} if effect else {}), **(moltres or {})}
    return build_test_state([
        {"active": attacker, "bench": list(attacker_bench)},
        {"active": holder, "bench": list(moltres_bench)},
    ], turn_number=turn, **kwargs)


def retaliation_damage(state):
    return [e for e in state.log if e["kind"] == "damage" and e.get("retaliation")]


PONYTA_ATTACKER = {"card": PONYTA, "energy": [FIRE, FIRE]}  # ほのおのしっぽ 30


class RegistrationTest(unittest.TestCase):
    def test_registered_with_the_latest_description(self):
        entry = DEFAULT_EFFECTS.attack_entry(ROCKETS_MOLTRES, 0)
        self.assertEqual(entry.effect, DamageAndRetaliation(retaliation=10))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("ほのおのかべ", PRINTED, LATEST, "P43 p.82"))
        attack = load_card_pool().get(ROCKETS_MOLTRES).attacks[0]
        self.assertEqual(([c.value for c in attack.cost], attack.damage, attack.text_ja), (["fire"] * 3, 40, PRINTED))  # W1〜W3
        self.assertTrue(attack.supported)


class EffectCreationTest(unittest.TestCase):
    """ほのおのかべを使う番（W1〜W5）。"""

    def moltres_turn(self, defender=MACHOP, **moltres):
        return build_test_state([
            {"active": {"card": ROCKETS_MOLTRES, "energy": [FIRE] * 3, **moltres}, "bench": [PONYTA]},
            {"active": defender, "bench": [MACHOP]},
        ], turn_number=5)

    def test_damage_then_effect_on_itself(self):
        """相手に 40（W2）→ 自分に持続する効果（W4。はたらくのは次の相手の番）。乱数を使わない。"""
        state = self.moltres_turn()
        start, rng = len(state.log), rng_fingerprint(state.rng)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(kinds(state, start)[:3], ["attack", "damage", "persistent_effect_added"])
        self.assertEqual(state.log[start + 1]["amount"], 40)
        moltres = state.players[0].active
        self.assertEqual(moltres.persistent_effects, (Retaliation(moltres.card, 0, 5, 6, 0, 10),))
        self.assertEqual(rng_fingerprint(state.rng), rng)
        self.assertEqual((state.turn_number, state.current_player), (6, 1))
        self.assertIsNotNone(retaliation(state, moltres))  # 次の相手の番（6 番）にはたらく

    def test_not_working_on_other_turns(self):
        """はたらくのは効果を与えた番の次の番だけ（W4・W5）。"""
        state = board(PONYTA_ATTACKER)
        moltres = state.players[1].active
        self.assertIsNotNone(retaliation(state, moltres))
        for turn in (TURN - 1, TURN + 1):
            other = state.clone()
            other.turn_number = turn
            self.assertIsNone(retaliation(other, moltres))

    def test_effect_even_if_the_damage_is_prevented_or_evaded(self):
        """相手が「ダメージを受けない」状態・「とうめい」で受けなかったときも、自分への効果は与える（説明に「ダメージを与えたら」がない）。"""
        prevented = self.moltres_turn(defender={"card": METAPOD, "evolved_from": CATERPIE, "prevent_damage": 4})
        prevented = apply_command(prevented, UseAttack(0, 0))
        order = kinds(prevented)
        self.assertLess(order.index("damage_prevented"), max(i for i, k in enumerate(order) if k == "persistent_effect_added"))
        self.assertEqual(len(prevented.players[0].active.persistent_effects), 1)
        evaded = with_coin_results(self.moltres_turn(defender={"card": HAUNTER, "evolved_from": GASTLY}), H)
        evaded = apply_command(evaded, UseAttack(0, 0))
        self.assertIn("attack_evaded", kinds(evaded))
        self.assertEqual(len(evaded.players[0].active.persistent_effects), 1)

    def test_expires_at_the_end_of_the_next_opponent_turn(self):
        """次の相手の番の終わりに消える（W5。p.89「効果の持続：次の相手の番の最後」）。番の終わりの turn_end の前、ポケモンチェックの前。"""
        state = apply_command(self.moltres_turn(), UseAttack(0, 0))
        state = apply_command(state, EndTurn(1))
        events = [e for e in state.log if e["kind"] in ("persistent_effect_removed", "turn_end")]
        self.assertEqual(events[-2]["kind"], "persistent_effect_removed")
        self.assertEqual((events[-2]["reason"], events[-2]["turn"]), ("expired", 6))
        self.assertEqual(state.players[0].active.persistent_effects, ())

    def test_used_again_after_it_expired(self):
        """同じポケモンが次の自分の番に再び使うと、新しい効果になる（前の効果は消えている。重ならない）。"""
        state = apply_command(self.moltres_turn(energy=[FIRE] * 3, damage=0), UseAttack(0, 0))
        state = apply_command(state, EndTurn(1))
        state = apply_command(state, UseAttack(0, 0))
        effects = state.players[0].active.persistent_effects
        self.assertEqual([(e.created_turn, e.active_turn) for e in effects], [(7, 8)])
        self.assertEqual(check_invariants(state), [])


class TriggerTest(unittest.TestCase):
    """相手の番（W11〜W21）。"""

    def test_counter_damage_to_the_attacker(self):
        """相手のワザによるダメージを受けたとき（W11）、ダメージを与えた相手の対戦ポケモンに 10（W14）。ログは retaliation のあとにダメージの要素。"""
        state = board(PONYTA_ATTACKER)
        start = len(state.log)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual(kinds(state, start)[:4], ["attack", "damage", "retaliation", "damage"])
        event = state.log[start + 3]
        self.assertEqual((event["player"], event["amount"], event["retaliation"], event["effect"]), (0, 10, True, str(FIRE_WALL)))
        self.assertEqual(state.log[start + 2]["trigger"], f"{PONYTA}#1")

    def test_zero_damage_does_not_trigger(self):
        """最終ダメージ 0（抵抗力 闘 −30）は「ダメージを受けなかった」（W13。p.319・p.321）。"""
        state = apply_command(board({"card": MACHOP, "energy": [FIGHTING]}), UseAttack(0, 0))  # けたぐり 20 − 30
        self.assertNotIn("retaliation", kinds(state))

    def test_weakness_applies(self):
        """弱点（W15。p.82）: バタフリー（弱点 炎）に 20。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        state = apply_command(board(butterfree), UseAttack(0, 0))
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:1]))
        event = retaliation_damage(state)[0]
        self.assertEqual((event["amount"], event["weakness"]), (20, True))

    def test_resistance_applies(self):
        """抵抗力（W16。p.82）: 炎の抵抗力 −30 のポケモン（テスト専用の記録。対応カードに炎の抵抗力を持つポケモンはない）で 10 − 30 = 0。"""
        extract = copy.deepcopy(read_extract())
        record = next(c for c in extract["cards"] if c["id"] == PONYTA)
        record["pokemon"]["resistances"] = [{"type": "fire", "operator": "-", "value": 30}]
        pool = pool_from_extract(extract)
        state = apply_command(board(PONYTA_ATTACKER, pool=pool), UseAttack(0, 1))
        event = retaliation_damage(state)[0]
        self.assertEqual((event["amount"], event["resistance"]), (0, True))

    def test_defender_on_the_attacker_applies(self):
        """ワザによるダメージなので、ワザを使ったポケモンについているディフェンダーで −20（W17。p.257・p.321）。"""
        state = apply_command(board({**PONYTA_ATTACKER, "trainers": [(DEFENDER, TURN + 1)]}), UseAttack(0, 1))
        event = retaliation_damage(state)[0]
        self.assertEqual(event["amount"], 0)
        self.assertEqual(event["modifiers"][0][0], 7)

    def test_chemical_gas_does_not_stop_it(self):
        """かがくへんかガスは特殊能力だけを消す（W18）。どちらの場のベトベトンでも、はたらく。"""
        muk = {"card": MUK, "evolved_from": GRIMER}
        for side in (0, 1):
            with self.subTest(side=side):
                state = board(PONYTA_ATTACKER, attacker_bench=[muk] if side == 0 else [RATTATA],
                              moltres_bench=[muk] if side == 1 else [PONYTA])
                state = apply_command(state, UseAttack(0, 1))
                self.assertEqual(len(retaliation_damage(state)), 1)

    def test_special_conditions_of_the_holder_do_not_stop_it(self):
        """R団のファイヤーが特殊状態でも、はたらく（W7。p.322「持続する効果」は特殊状態と重複する）。"""
        for condition in ({"sleep": True}, {"paralysis": 6}, {"confusion": True}, {"poison": 10}):
            with self.subTest(condition=condition):
                state = apply_command(board(PONYTA_ATTACKER, moltres=condition), UseAttack(0, 1))
                self.assertEqual(len(retaliation_damage(state)), 1)

    def test_transparency_of_the_attacker(self):
        """ワザによるダメージなので、ゴーストの「とうめい」（W19）: 「おもて」なら受けない、「うら」なら受ける。コインはゴースト側のプレイヤー。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        heads = apply_command(with_coin_results(board(haunter), H), UseAttack(0, 0))
        self.assertEqual(retaliation_damage(heads), [])
        evade = next(e for e in heads.log if e["kind"] == "evade_check")
        self.assertEqual((evade["player"], evade["effect"], evade["attacker"]), (0, str(FIRE_WALL), 1))
        tails = apply_command(with_coin_results(board(haunter), T), UseAttack(0, 0))
        self.assertEqual(retaliation_damage(tails)[0]["amount"], 10)

    def test_counterattack_of_the_attacker_and_no_chain(self):
        """「ほのおのかべ」のダメージはワザによるダメージなので、ワザを使ったカイリキーの「はんげき」がはたらき、R団のファイヤーに 10（W20）。
        「はんげき」のダメージは特殊能力によるダメージなので、「ほのおのかべ」は再びはたらかない（連鎖しない）。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "energy": [FIGHTING] * 4}
        state = apply_command(board(machamp), UseAttack(0, 0))
        self.assertEqual([k for k in kinds(state) if k in ("damage", "retaliation", "counterattack")],
                         ["damage", "retaliation", "damage", "counterattack"])
        counter = next(e for e in state.log if e["kind"] == "counterattack")
        self.assertEqual((counter["attacker"], counter["effect"], counter["total_damage"]), (1, str(FIRE_WALL), 40))

    def test_order_after_damage_before_effects(self):
        """ダメージの処理のあと、ダメージ以外の効果の前（W21。p.89）: どくばりのコインより先・でんげきの自分へのダメージより後。"""
        weedle = apply_command(with_coin_results(board({"card": WEEDLE, "energy": [GRASS]}), H), UseAttack(0, 0))
        order = [k for k in kinds(weedle) if k in ("damage", "retaliation", "coin_flip", "special_condition")]
        self.assertEqual(order[:5], ["damage", "retaliation", "damage", "coin_flip", "special_condition"])
        pikachu = apply_command(with_coin_results(board({"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}), T), UseAttack(0, 1))
        damages = [e for e in pikachu.log if e["kind"] in ("damage", "retaliation")]
        self.assertEqual([(e["kind"], e.get("target"), e.get("retaliation")) for e in damages],
                         [("damage", None, None), ("damage", "self", None), ("retaliation", None, None), ("damage", None, True)])

    def test_damage_swap_is_not_damage(self):
        """ダメージカウンターの移動は「ダメージを受けた」ことにならない（p.320）。ダメージスワップは持ち主の番だけ（効果がはたらくのは相手の番）
        なので、効果がはたらいている R団のファイヤーに相手がカウンターをのせることはない（D4。テストは持ち主の番に効果がはたらかないことで確かめる）。"""
        state = build_test_state([
            {"active": {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "damage": 30}, "bench": [{"card": ROCKETS_MOLTRES, "retaliation": 6}]},
            {"active": MACHOP},
        ], turn_number=7)
        self.assertNotEqual(check_invariants(state), [])  # ベンチに持続する効果は残らない（p.322）


class KnockOutTest(unittest.TestCase):
    """きぜつ（W22〜W24）と消える契機（W6・W8〜W10）。"""

    def test_moltres_knocked_out_still_hits(self):
        """R団のファイヤーがそのダメージできぜつしても与える（W22。「それによってこのカードが「きぜつ」しても」）。そのあと「ふしちょう」。"""
        state = apply_command(board(PONYTA_ATTACKER, moltres={"damage": 30}), UseAttack(0, 1))
        self.assertEqual(retaliation_damage(state)[0]["amount"], 10)
        removed = next(e for e in state.log if e["kind"] == "persistent_effect_removed")
        self.assertEqual(removed["reason"], "knock_out")  # W8（p.322「場をはなれたら」）
        state = apply_command(state, TakePrize(0, 0))
        self.assertEqual(state.decision.kind, POST_KNOCKOUT_POWER)

    def test_attacker_knocked_out_by_the_counter_damage(self):
        """「ほのおのかべ」のダメージでワザを使ったポケモンがきぜつする（W23）: きぜつの処理はワザのあと。サイドは R団のファイヤーの持ち主。"""
        state = apply_command(board({**PONYTA_ATTACKER, "damage": 30}), UseAttack(0, 1))
        self.assertEqual([(e["kind"], e["player"]) for e in state.log if e["kind"] in ("knock_out", "turn_end")], [("knock_out", 0)])
        self.assertEqual((state.phase, state.decision.player), (Phase.TAKE_PRIZE, 1))

    def test_attacker_knocked_out_skips_its_own_heal_but_not_the_whirlwind(self):
        """きぜつしたワザを使ったポケモン自身への効果（メガドレインの回復）は処理しない（p.89 の「スターブーメラン」の例。v0.10 の C16）。
        相手への効果（ふきとばし）は処理する（p.89 の「ふきとばし」の例）。ふきとばしでベンチにもどった R団のファイヤーの効果は消える（W6）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "damage": 50, "energy": [GRASS] * 4}
        drained = apply_command(board(butterfree), UseAttack(0, 1))
        self.assertIn("drain_heal_skipped", kinds(drained))
        blown = apply_command(board(butterfree), UseAttack(0, 0))
        self.assertEqual((blown.phase, blown.decision.player), (Phase.DECISION, 1))  # 相手が入れ替えるポケモンを選ぶ（バタフリーは HP 以上のまま）
        self.assertGreaterEqual(blown.players[0].active.damage, 70)
        self.assertEqual(check_invariants(blown), [])
        d = blown.decision
        blown = apply_command(blown, ResolveDecision(d.player, d.id, d.options[:1]))
        removed = [e for e in blown.log if e["kind"] == "persistent_effect_removed"]
        self.assertEqual(removed[0]["reason"], "forced_switch")
        self.assertEqual(blown.players[1].bench[0].persistent_effects, ())

    def test_attacker_already_knocked_out_by_its_own_damage(self):
        """ワザを使ったポケモンが同じワザの自分へのダメージですでに HP 以上なら与えない（retaliation_skipped。W23・v0.10 の C15）。"""
        machoke = {"card": MACHOKE, "evolved_from": MACHOP, "damage": 60, "energy": [FIGHTING] * 4}
        state = apply_command(board(machoke), UseAttack(0, 1))
        skipped = next(e for e in state.log if e["kind"] == "retaliation_skipped")
        self.assertEqual(skipped["reason"], "knocked_out")
        self.assertEqual(retaliation_damage(state), [])

    def test_return_to_hand_and_play_again_does_not_bring_it_back(self):
        """きぜつで消え（W8）、「ふしちょう」で手札にもどしてもう一度場に出しても復活しない（W9・W10。p.322「一度消えた「持続する効果」は
        復活しません」）。"""
        from kyuura_engine import PlayBasicToBench
        state = apply_command(board(PONYTA_ATTACKER, moltres={"damage": 30}), UseAttack(0, 1))
        card = state.players[1].active.card if state.players[1].active else next(
            e["pokemon"] for e in state.log if e["kind"] == "knock_out" and e["player"] == 1)
        state = apply_command(state, TakePrize(0, 0))
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options))  # 使う
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:1]))  # バトル場に出す → 番が終わる
        state = apply_command(state, PlayBasicToBench(1, card))
        again = next(pk for pk in state.players[1].bench if pk.card == card)
        self.assertEqual(again.persistent_effects, ())
        self.assertEqual(check_invariants(state), [])

    def test_turn_player_guts_after_counter_damage(self):
        """番のプレイヤーのサカキのカイリキーが「ほのおのかべ」のダメージ（相手のワザによるダメージ）で HP 以上 → 番のプレイヤーが「こんじょう」を
        使うか決める（v0.11 の G3 の「相手のワザによるダメージ」に当たる。SUPPORTED）。ハリケーンパンチでは R団のファイヤーがきぜつしうるので
        W24 で止まる（対応カードでは起こらない）。テスト専用の効果（相手に 40）を同じ位置に登録して確かめる。"""
        attack = load_card_pool().get(GIOVANNIS_MACHAMP).attacks[0]

        class Punch(AttackEffect):
            implementation_id = "test_punch"

            def damage_profile(self, state, use):
                return DamageProfile(opponent=(40,))

            def resolve(self, state, use):
                deal_attack_damage(state, use, OPPONENT_ACTIVE, 40)

        effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(GIOVANNIS_MACHAMP, 0): AttackEntry(Punch(), attack.name_ja, attack.text_ja)})
        giovanni = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "damage": 90, "energy": [FIGHTING] * 4}
        state = apply_command(with_coin_results(board(giovanni, effects=effects), H), UseAttack(0, 0))
        d = state.decision
        self.assertEqual((d.kind, d.player, d.options), (KO_PREVENTION, 0, (state.players[0].active.pokemon_id,)))
        self.assertEqual(check_invariants(state), [])
        state = apply_command(state, ResolveDecision(0, d.id, d.options))
        self.assertIn("ko_prevented", kinds(state))
        self.assertEqual(state.players[0].active.damage, 90)

    def test_hurricane_punch_is_stopped(self):
        """ハリケーンパンチ（コイン 4 枚。最大 120 − 30 = 90）では R団のファイヤーがきぜつしうるので、W24 で宣言の前に止まる。"""
        giovanni = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "damage": 90, "energy": [FIGHTING] * 4}
        state = board(giovanni)
        before, rng = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT")
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))


class CoinIndependenceTest(unittest.TestCase):
    def test_acceptance_does_not_depend_on_the_coins(self):
        """「ほのおのかべ」の効果がはたらく R団のファイヤーに、対応カードのどのワザを使っても、受け付けるか・拒否のコードがコインの結果（8 通り）
        で変わらない（W24 はコインのどの結果でもそうなりうるなら止める）。"""
        checked = 0
        for (card, index), moltres_damage, attacker_damage in itertools.product(ATTACKS, (0, 30, 50), (0, 30)):
            shift = 2 * len(EVOLVED_FROM.get(card, ()))
            hp = load_card_pool().get(card).hp
            attacker = {"card": card, "energy": energy_for(card, index), "damage": min(attacker_damage, hp - 10)}
            if card in EVOLVED_FROM:
                attacker.update(evolved_from=list(EVOLVED_FROM[card]), evolved_turn=1 + shift)
            if card == ROCKETS_MOLTRES:
                continue  # 相手の番に、相手の R団のファイヤーが使う（ここでは攻撃する側）。ミラーは下で別に確かめる
            state = board(attacker, moltres={"damage": moltres_damage}, turn=TURN + shift)
            results = set()
            for coins in itertools.product((H, T), repeat=3):
                try:
                    new = apply_command(with_coin_results(state, *coins), UseAttack(0, index))
                    self.assertEqual(check_invariants(new), [])
                    results.add("accepted")
                except EngineError as error:
                    results.add(error.code)
            with self.subTest(card=card, index=index, moltres=moltres_damage, attacker=attacker_damage):
                self.assertEqual(len(results), 1, results)
            checked += 1
        self.assertGreater(checked, 90)


class SaveRestoreAndInvariantTest(unittest.TestCase):
    """効果がはたらいている状態の保存・復元（D5 の 5〜8）・書き出し・不変条件。"""

    def test_pickle_deepcopy_clone_keep_the_effect(self):
        state = board(PONYTA_ATTACKER)
        for copied in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
            with self.subTest(kind=type(copied).__name__):
                self.assertEqual(full(copied), full(state))
                self.assertEqual(copied.players[1].active.persistent_effects, state.players[1].active.persistent_effects)
                self.assertEqual(full(apply_command(copied, UseAttack(0, 1))), full(apply_command(state, UseAttack(0, 1))))
                self.assertEqual(full(apply_command(copied, EndTurn(0))), full(apply_command(state, EndTurn(0))))  # 期限で消える

    def test_serialization(self):
        """形式 8・9 は種類 ``retaliation`` に ``attack_index``・``amount`` を加える（形式 9 のまま）。形式 1〜7 は ValueError。"""
        state = board(PONYTA_ATTACKER)
        effect = state_to_dict(state, format_version=9)["players"][1]["active"]["persistent_effects"]
        self.assertEqual(effect, [{"effect": "retaliation", "source_card": state.players[1].active.card, "source_card_id": ROCKETS_MOLTRES,
                                   "source_player": 1, "created_turn": TURN - 1, "active_turn": TURN, "attack_index": 0, "amount": 10}])
        for version in range(1, 8):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        self.assertEqual(serialization_problems(state), [])

    def test_invariants(self):
        """ワザの位置・与えるダメージが登録と違う・ベンチにある・期限を過ぎて残る効果は、不変条件の違反。"""
        state = board(PONYTA_ATTACKER)
        moltres = state.players[1].active
        for change in ({"amount": 20}, {"attack_index": 1}, {"active_turn": TURN + 1}):
            broken = state.clone()
            target = broken.players[1].active
            target.persistent_effects = (dataclasses.replace(target.persistent_effects[0], **change),)
            with self.subTest(change=change):
                self.assertNotEqual(check_invariants(broken), [])
        self.assertEqual(check_invariants(state), [])
        self.assertEqual(moltres.persistent_effects[0].kind, "retaliation")

    def test_invalid_commands_change_nothing(self):
        state = board({**PONYTA_ATTACKER, "energy": [FIRE]})
        before, rng = full(state), rng_fingerprint(state.rng)
        for command in (UseAttack(0, 1), UseAttack(1, 0), Retreat(0, (), 0), UsePokemonPower(0, 1, 0)):
            with self.subTest(command=command):
                with self.assertRaises(EngineError):
                    apply_command(state, command)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))


if __name__ == "__main__":
    unittest.main()
