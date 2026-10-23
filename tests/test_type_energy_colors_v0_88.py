"""v0.88（docs/type-energy-colors-v0.88.md）: ポケモンのタイプとエネルギーの色を変える特殊能力、色を選ぶ・数えるワザ、変えたカードをつけ替える特殊能力の 11 枚。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P321-DAMAGE-ORDER・GR-2000-P325-SAME-TIMING・
CR-ENERGY-TRANS-NOT-ATTACHMENT・CR-CHEMICAL-GAS-PRIOR-RESULTS など。docs 各章）。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。
"""

from __future__ import annotations

import json
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.effects import PowerKey
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import observe
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.test_entry_powers_energy_lifecycle_v0_85 import (
    evolve,
    light_dragonite,
    meganium,
    power,
    stage1,
    stage2,
    togetic,
)
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    new_events,
    rejects,
    snapshot,
)
from tests.test_shining_gentle_v0_83 import answer, board, mon, play

HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, F, G, L, P, FT = H.WATER, H.FIRE, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIGHTING
MIR = H.MIRACLE_ENERGY
MEW1 = "UNRESOLVED_MIRACLE_ENERGY_UNDER_WIND"
CE1, CE2, CE3 = "UNRESOLVED_COLOR_EFFECT_CONTINUATION", "UNRESOLVED_COLOR_REPLACEMENT_ORDER", "UNRESOLVED_COLOR_CHANGED_ENERGY_CARD"
COLOR = {c: E.COLORS.index(c) for c in E.COLORS}
V088_ATTACKS = [AttackKey(c, i) for c in H.V0_88_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]
V088_POWERS = [PowerKey(c, 0) for c in (H.LANTURN_NEO1, H.LANTURN_NEO3, H.PORYGON2_NEO3, H.ERIKAS_ODDISH_GD4, H.MAGNETON_NEO3)]


def hide(state, card_id, player=0):
    """マチスの秘策を使い、手札の ``card_id`` をうらにしてベンチに出す（公開のコマンドだけ）。"""
    choosing = play(state, H.LT_SURGES_SECRET_PLAN, player=player)
    uid = next(u for u in choosing.decision.options if choosing.cards[u].card_id == card_id)
    return answer(choosing, (uid,))


# ---------------------------------------------------------------- 1 章: 前段の修正（うらのカードのある場の is_face_down の引数）


class FaceDownArgumentRegressionTest(unittest.TestCase):
    """v0.85 で加えた 6 か所が ``GameState.is_face_down`` に場のポケモンでなくカードの uid（整数）を渡し、場にうらのカード（v0.67。マチスの秘策）が 1 枚でもあると
    ``AttributeError`` になっていた（``face_down_cards`` が空なら短絡評価で起こらない）。固定した v0.87（``81a5c5c``）ではどのテストも ``AttributeError`` になる（docs 1 章）。
    盤面は整合性のあるテストの盤面から公開のコマンドでうらのカードを置いたもので、``new_game`` からの自然な対戦で見つけたものではない。"""

    def wild_growth_board(self, *, hidden=W, secret=True, bench_meganium=True):
        hand = (H.LT_SURGES_SECRET_PLAN, hidden) if secret else ()
        bench = (meganium(),) if bench_meganium else (mon(H.RATTATA),)
        state = board(stage1(H.BAYLEEF_NEO1, (G, G), base=H.CHIKORITA_NEO1), bench=bench, hand=hand, opponent=mon(H.CHANSEY))
        return hide(state, hidden) if secret else state

    def test_wild_growth_payment_with_a_face_down_card(self):
        """［おいしげる］（メガニウム neo1-014）がはたらく場で、ダブルはっぱカッター（草草草）を「草」2 枚で払える（2 枚が「草」4 個）。うらのカードがあってもなくても同じ。"""
        for secret in (False, True):
            with self.subTest(secret=secret):
                state = self.wild_growth_board(secret=secret)
                self.assertEqual(len(state.face_down_cards), int(secret))
                before = snapshot(state)
                done = apply_kernel(state, UseAttack(0, 1))
                self.assertEqual(snapshot(state), before)  # 渡した状態は変えない
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [40])
                audited(self, done)
        without = self.wild_growth_board(bench_meganium=False)
        rejects(self, without, UseAttack(0, 1), "INSUFFICIENT_ENERGY", error=IllegalActionError)

    def test_hidden_identity_and_owner_do_not_change_the_answer(self):
        """うらのカードの本当のカード（水エネルギー・ラッタ・草エネルギー）を変えても、受け付けるか・結果・相手の観測は同じ。うらのカードが相手の場にあっても同じ。"""
        outcomes = set()
        for hidden in (W, H.RATTATA, G):
            state = self.wild_growth_board(hidden=hidden)
            done = apply_kernel(state, UseAttack(0, 1))
            seen = json.dumps(observe(done, 1)["players"][0]["bench"], sort_keys=True, ensure_ascii=False)
            outcomes.add((tuple(e["amount"] for e in new_events(state, done, "damage")), done.players[1].active.damage, seen))
        self.assertEqual(len(outcomes), 1)
        their_bayleef = mon(H.BAYLEEF_NEO1, (G, G), played_turn=2, evolved_from=H.CHIKORITA_NEO1, evolved_turn=4)
        their_meganium = mon(H.MEGANIUM_NEO1, played_turn=2, evolved_from=[H.CHIKORITA_NEO1, H.BAYLEEF_NEO1], evolved_turn=6)
        theirs = board(mon(H.CHANSEY), bench=(), opponent=their_bayleef, opponent_bench=(their_meganium,), opponent_hand=(H.LT_SURGES_SECRET_PLAN, W),
                       current=1, turn=8)
        hidden = hide(theirs, W, player=1)
        done = apply_kernel(hidden, UseAttack(1, 1))
        self.assertEqual(([e["amount"] for e in new_events(hidden, done, "damage")], done.players[0].active.damage), ([40], 40))
        audited(self, done)
        mine = board(stage1(H.BAYLEEF_NEO1, (G, G), base=H.CHIKORITA_NEO1), bench=(meganium(),), opponent=mon(H.CHANSEY),
                     opponent_hand=(H.LT_SURGES_SECRET_PLAN, W), current=1, turn=8)
        mine = apply_kernel(hide(mine, W, player=1), EndTurn(1))  # うらのカードが相手（攻撃されるほう）の場にある
        self.assertEqual(len(mine.face_down_cards), 1)
        done = apply_kernel(mine, UseAttack(0, 1))
        self.assertEqual([e["amount"] for e in new_events(mine, done, "damage")], [40])
        audited(self, done)

    def test_miracle_energy_under_wind_with_a_face_down_card(self):
        """ミラクルエネルギー（neo4-113）と［きせきのかぜ］（やさしいカイリュー）の場の確かめ（``miracle_energy_problems``）。うらのカードを置くコマンドを受け付け、番の終わりは
        今までどおり MEW1 で止まる。"""
        state = board(togetic((MIR,)), opponent=light_dragonite(), hand=(H.LT_SURGES_SECRET_PLAN, W))
        hidden = hide(state, W)
        self.assertEqual(len(hidden.face_down_cards), 1)
        audited(self, hidden)
        halted = apply_kernel(hidden, EndTurn(0))
        self.assertEqual((halted.phase, halted.halt.code), (Phase.HALTED, MEW1))

    def test_herbal_scent_targets_with_a_face_down_card(self):
        """［ハーブのかおり］（メガニウム PF1-003）の対象。うらのカード（ダメージを持たない）は数えず、ほかの「草」ポケモンは回復する。"""
        state = board(stage1(H.BAYLEEF_PF1, (G,), base=H.CHIKORITA_NEO1, damage=40), bench=(mon(H.CHIKORITA_NEO1, damage=10),),
                      hand=(H.MEGANIUM_PF1, H.LT_SURGES_SECRET_PLAN, W))
        asking = evolve(hide(state, W), H.MEGANIUM_PF1)
        self.assertEqual(asking.decision.kind, "entry_power")
        done = answer(with_coin_results(asking, HD), asking.decision.options)
        self.assertEqual([p.damage for p in done.players[0].in_play() if not done.is_face_down(p)], [0, 0])
        audited(self, done)

    def test_fire_recharge_targets_with_a_face_down_card(self):
        """［ファイヤーリチャージ］（バクフーン neo1-021）のつける先。うらのカードは選べるものに入らない。"""
        state = board(stage2(H.TYPHLOSION_NEO1, line=(H.CYNDAQUIL_NEO1, H.QUILAVA_PF1)), bench=(mon(H.CHARMANDER),), discard=(F,),
                      hand=(H.LT_SURGES_SECRET_PLAN, W))
        hidden = hide(state, W)
        card = power(hidden, coins=(HD,))
        target = answer(card, card.decision.options)
        self.assertEqual(target.decision.options, (hidden.players[0].active.pokemon_id, hidden.players[0].bench[0].pokemon_id))
        audited(self, answer(target, target.decision.options[:1]))

    def test_static_electricity_count_with_a_face_down_card(self):
        """せいでんき（メリープ neo1-038）の数はおたがいの場の「メリープ」で、うらのカードは数えない（2 匹 → 最大 2 枚）。"""
        state = board(mon(H.MAREEP_NEO1, (L,)), bench=(H.MAREEP_NEO2,), deck=[L] * 4 + [W] * 4, hand=(H.LT_SURGES_SECRET_PLAN, W))
        choosing = apply_kernel(hide(state, W), UseAttack(0, 0))
        self.assertEqual(choosing.decision.max_choices, 2)
        audited(self, answer(choosing, choosing.decision.options[:2]))




class SplitObservationRegressionTest(unittest.TestCase):
    """v0.87 の［ぶんれつ］（ドガース ES2-003）の決定（``split_from_deck``）は、決めるプレイヤーが自分の山札をさがすのに観測の ``DECK_REVEALING_KINDS`` になく、決めるプレイヤーの観測の
    選べるものに見えないカードの uid があることになり、監査の選べるものの数を隠す一覧にもなかった（v0.88 の検証用の対戦で見つけた。固定した v0.87 ではどちらも
    ``observation_problems`` が問題を返す）。決めるプレイヤーには山札のドガースが見え、ほかの人には種類と決めるプレイヤーだけが見える。"""

    def test_split_decision_observation(self):
        from tests.log_audit import observation_problems

        for deck in ([H.KOFFING_ES2, W, W], [W, W, W]):
            with self.subTest(deck=deck):
                state = board(mon(H.RATTATA, (H.DOUBLE_COLORLESS_ENERGY,)), opponent=mon(H.KOFFING_ES2), opponent_deck=deck)
                asked = apply_kernel(state, UseAttack(0, 0))
                self.assertEqual(asked.decision.kind, "split_from_deck")
                self.assertEqual(observation_problems(asked), [])
                mine = observe(asked, 1)["decision"]
                self.assertEqual([o.get("card_id") for o in mine["options"]], [H.KOFFING_ES2] * (deck[0] == H.KOFFING_ES2))
                self.assertEqual(observe(asked, 0)["decision"], {"kind": "split_from_deck", "player": 1})


class KnockOutBookkeepingRegressionTest(unittest.TestCase):
    """直前のきぜつをログの終わりから読む確かめ（サイドの並び・「ふしちょう」の候補）は、きぜつのあとの記録（持続する効果の消去・v0.82 のリサイクルエネルギーのもどし・v0.88 の
    ［せんすい］の記録の消去 ``target_gone``）を読み飛ばす（``engine._knockout_bookkeeping``）。v0.82〜v0.87 の「ふしちょう」の確かめはリサイクルエネルギーのもどしを読み飛ばさず、
    リサイクルエネルギーのついた R団のファイヤーがきぜつすると ``StateIntegrityError`` になっていた（固定した v0.87 で再現する。docs 8 章）。"""

    def test_phoenix_with_recycle_energy(self):
        state = board(mon(H.HITMONCHAN, (FT, FT, FT)), opponent=mon(H.ROCKETS_MOLTRES, (H.RECYCLE_ENERGY,), damage=50))
        done = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual([e["kind"] for e in new_events(state, done)][-2:], ["knock_out", "energy_returned_to_hand"])
        self.assertEqual(done.decision.kind, "take_prize")
        audited(self, done)
        asked = answer(done, done.decision.options[:1])
        self.assertEqual(asked.decision.kind, "post_knockout_power")
        audited(self, asked)

    def test_submerge_source_knocked_out(self):
        """［せんすい］を使ったランターンが、相手のマチスのマルマインの［ショックボム］のダメージでワザのあとにきぜつしたら、記録はコマンドの終わりに消える（``target_gone``）。
        そのあとのサイドの決定を受け付ける（v0.88 の検証用の対戦で見つけた盤面）。"""
        electrode = mon(H.LT_SURGES_ELECTRODE, played_turn=2, evolved_from="PMCG5-038", evolved_turn=4)
        state = submerged(board(lanturn3((L, W, W), damage=70), opponent=electrode))
        done = apply_kernel(with_coin_results(state, TL, TL), UseAttack(0, 0))
        self.assertIn("target_gone", [e["reason"] for e in new_events(state, done, "color_effect_removed")])
        self.assertEqual((done.color_effects, done.decision.kind), ((), "take_prize"))
        audited(self, done)

# ---------------------------------------------------------------- 共通の盤面


def lanturn1(energy=(L, L, W, W), **extra):
    return stage1(H.LANTURN_NEO1, energy, base=H.CHINCHOU_NEO1, **extra)


def lanturn3(energy=(L, W, W), **extra):
    return stage1(H.LANTURN_NEO3, energy, base=H.CHINCHOU_NEO1, **extra)


def porygon2(energy=(W, W, W), **extra):
    return stage1(H.PORYGON2_NEO3, energy, base=H.PORYGON, **extra)


def magneton(energy=(L, L, W), **extra):
    return stage1(H.MAGNETON_NEO3, energy, base=H.MAGNEMITE, **extra)


def muk(opponent=True):
    """かがくへんかガスのベトベトン（相手の場なら相手の番に進化した盤面）。"""
    return mon(H.MUK, played_turn=2, evolved_from=H.GRIMER, evolved_turn=4) if opponent else stage1(H.MUK, base=H.GRIMER)


def erikas_vileplume(energy=()):
    """相手の場のエリカのラフレシア（［ぼうぎょかふん］）。"""
    return mon(H.ERIKAS_VILEPLUME, energy, played_turn=2, evolved_from=[H.ERIKAS_ODDISH, H.ERIKAS_GLOOM], evolved_turn=6)


def damages(before, after):
    """ダメージのログの (受けたポケモンのいちばん上のカード, 量)。"""
    return [(e["pokemon"], e["amount"]) for e in new_events(before, after, "damage")]


def convert(state, holder, uid, color, user=None):
    """ポリゴン2の［エナジーコンバーター］で、``holder`` についているカード ``uid`` のエネルギーの色を ``color`` にする（公開のコマンドだけ）。"""
    user = next(p for p in state.players[0].in_play() if state.card_def(p.card).id == H.PORYGON2_NEO3) if user is None else user
    asking = apply_kernel(state, UsePokemonPower(0, user.pokemon_id, 0, energy=uid, source=holder.pokemon_id))
    return answer(asking, (COLOR[color],))


def submerged(state):
    return apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))


# ---------------------------------------------------------------- 7 章: 登録・写し・記録


class RegistrationTest(unittest.TestCase):
    """11 枚のどのワザ（15）・どの特殊能力（5）も登録し、写しの名前・文面と照らす。v0.88 の登録を除くと v0.87 の 1,080 枚にもどる。"""

    def test_every_attack_and_power_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(len(V088_ATTACKS), 15)
        for key in V088_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                self.assertIsNotNone(entry)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja), (attack.name_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
        for key in V088_POWERS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
                power = pool.definitions[key.card_id].powers[key.power_index]
                self.assertEqual((entry.name_ja, entry.text_ja), (power.name_ja, power.text_ja))
                self.assertEqual(entry.effect.check(power), [])
        for card in H.V0_88_CARDS:
            self.assertIn(card, pool.playable_ids)

    def test_unregistered_without_the_v0_88_entries(self):
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V088_ATTACKS).without_powers(DEFAULT_EFFECTS.id, V088_POWERS)
        pool = pool_from_extract(read_extract(), registry)
        for card in H.V0_88_CARDS:
            with self.subTest(card=card):
                self.assertNotIn(card, pool.playable_ids)
        self.assertEqual(len(pool.playable_ids), 1080)
        self.assertEqual(len(load_card_pool().playable_ids), 1091)

    def test_same_data_cards_share_registrations(self):
        for index in (0, 1):
            self.assertIs(DEFAULT_EFFECTS.attack_entry(H.PORYGON_QSG, index), DEFAULT_EFFECTS.attack_entry(H.PORYGON_ES1, index))
        self.assertIsNot(DEFAULT_EFFECTS.attack_entry(H.COOL_PORYGON, 1), DEFAULT_EFFECTS.attack_entry(H.PORYGON_ES1, 0))  # 3Dアタックの数（20）と文面が違う

    def test_new_types_are_not_in_the_v0_13_verified_list(self):
        from kyuura_engine.resolution.v013_checks import VERIFIED

        for effect_type in (E.ChosenColorEnergySpreadDamage, E.OwnBasicColorTypeSpreadDamage, E.PlusDistinctBasicEnergyColors, E.ChangeOwnResistanceOptional,
                            E.ChangeWeaknessAndResistanceOptional):
            self.assertIn(effect_type, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertNotIn(effect_type, VERIFIED)

    def test_text_variants_are_not_accepted_by_older_types(self):
        """「変えてよい」のテクスチャー2は v0.48 の ``ChangeOwnResistance``（「かえる」）では受け付けない。デルタビームの 3 つの特殊状態は 4 つの既定と違う。"""
        pool = load_card_pool()
        self.assertNotEqual(E.ChangeOwnResistance().check(pool.definitions[H.PORYGON_ES1].attacks[1]), [])
        self.assertNotEqual(E.DamageThenChosenStatusOnHeads().check(pool.definitions[H.PORYGON2_NEO3].attacks[0]), [])


# ---------------------------------------------------------------- 5.1 節: ［すいりょくはつでん］（ランターン neo1-040）


class HydroelectricTest(unittest.TestCase):

    def test_extra_water_energy_adds_damage_only_when_used(self):
        """「まぶしいひかり」（雷雷 20）といっしょに使うと、多い「水」エネルギー 1 個につき 10 を 2 段階に足す（「水」2 枚 → 40）。使わなければ 20。"""
        for energy, used, expected in (((L, L, W, W), True, 40), ((L, L, W, W), False, 20), ((L, L, W), True, 30), ((L, L), True, 20)):
            with self.subTest(energy=energy, used=used):
                state = board(lanturn1(energy), opponent=mon(H.CHANSEY))
                done = apply_kernel(with_coin_results(state, TL), UseAttack(0, 0, attack_power=used))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [expected])
                self.assertEqual(len(new_events(state, done, "attack_power")), int(used))
                audited(self, done)

    def test_converted_card_counts_as_water(self):
        """［エナジーコンバーター］で「水」にした雷エネルギーカードも「水」エネルギー（説明はエネルギーを数える）。支払いに要る雷 2 個は残りの雷で払う。"""
        state = board(lanturn1((L, L, L)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
        lanturn = state.players[0].active
        changed = convert(state, lanturn, lanturn.energy[2], EnergyType.WATER)
        done = apply_kernel(with_coin_results(changed, TL), UseAttack(0, 0, attack_power=True))
        self.assertEqual([e["amount"] for e in new_events(changed, done, "damage")], [30])
        audited(self, done)

    def test_rejections(self):
        """``UsePokemonPower`` では使えない。ほかのワザ・持たないポケモン・こんらん・かがくへんかガス・数え方の決まらないレインボーエネルギーでは、宣言のときに拒否する（状態は変わらない）。"""
        state = board(lanturn1(), opponent=mon(H.CHANSEY))
        rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POWER_NOT_USABLE_NOW", error=IllegalActionError)
        other = board(lanturn3((L, W, W)), opponent=mon(H.CHANSEY))
        rejects(self, other, UseAttack(0, 0, attack_power=True), "ATTACK_POWER_NOT_AVAILABLE", error=IllegalActionError)
        confused = board(lanturn1(confusion=True), opponent=mon(H.CHANSEY))
        rejects(self, confused, UseAttack(0, 0, attack_power=True), "POKEMON_CONFUSED", error=IllegalActionError)
        gas = board(lanturn1(), opponent=mon(H.CHANSEY), opponent_bench=(muk(),))
        rejects(self, gas, UseAttack(0, 0, attack_power=True), "POWER_SUPPRESSED", error=IllegalActionError)
        rainbow = board(lanturn1((L, L, H.RAINBOW_ENERGY)), opponent=mon(H.CHANSEY))
        rejects(self, rainbow, UseAttack(0, 0, attack_power=True), "UNRESOLVED_RAINBOW_ENERGY_TYPE")
        done = apply_kernel(with_coin_results(rainbow, TL), UseAttack(0, 0))  # 使わなければ止めない
        self.assertEqual([e["amount"] for e in new_events(rainbow, done, "damage")], [20])

    def test_serialization_of_the_command(self):
        from kyuura_engine.commands import command_from_dict, command_to_dict

        self.assertNotIn("attack_power", command_to_dict(UseAttack(0, 0)))
        command = UseAttack(0, 0, attack_power=True)
        self.assertEqual(command_from_dict(command_to_dict(command)), command)


# ---------------------------------------------------------------- 5.2 節: ［せんすい］（ランターン neo3-026）


class SubmergeTest(unittest.TestCase):

    def test_type_changes_until_the_end_of_the_turn(self):
        state = board(lanturn3(), opponent=mon(H.CHANSEY))
        done = submerged(state)
        lanturn = done.players[0].active
        self.assertEqual(E.type_readings(done, lanturn), (EnergyType.WATER,))
        self.assertEqual((E.weakness_of(done, lanturn), E.resistance_of(done, lanturn)[0]), (EnergyType.FIGHTING, None))  # タイプだけ
        self.assertEqual(observe(done, 1)["players"][0]["active"]["pokemon_type"], "water")
        rejects(self, done, UsePokemonPower(0, lanturn.pokemon_id, 0), "POWER_ALREADY_USED", error=IllegalActionError)
        audited(self, done)
        ended = apply_kernel(done, EndTurn(0))
        self.assertEqual(ended.color_effects, ())
        self.assertEqual([e["reason"] for e in new_events(done, ended, "color_effect_removed")], ["expired"])
        self.assertEqual(E.type_readings(ended, ended.players[0].active), (EnergyType.LIGHTNING,))
        audited(self, ended)

    def test_the_attack_damage_uses_the_new_type(self):
        """アクアフラッシュ（30）は、弱点「水」のヒトカゲには 60、弱点「雷」のゼニガメには 30（せんすいのあと）。使わなければ逆。"""
        for opponent, used, expected in ((H.CHARMANDER, True, 60), (H.SQUIRTLE, True, 30), (H.CHARMANDER, False, 30), (H.SQUIRTLE, False, 60)):
            with self.subTest(opponent=opponent, used=used):
                state = board(lanturn3(), opponent=mon(opponent, (W,)))
                if used:
                    state = submerged(state)
                done = apply_kernel(with_coin_results(state, TL), UseAttack(0, 0))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [expected])
                audited(self, done)

    def test_confusion_ends_the_effect(self):
        """エリカのラフレシアの［ぼうぎょかふん］でこんらん状態になったら、効果も消える（回復しても戻らない。記録を消す）。"""
        state = submerged(board(lanturn3(), opponent=erikas_vileplume()))
        done = apply_kernel(with_coin_results(state, HD, TL), UseAttack(0, 0))
        self.assertTrue(done.players[0].active.conditions.confused)
        self.assertEqual(done.color_effects, ())
        self.assertEqual([e["reason"] for e in new_events(state, done, "color_effect_removed")], ["special_condition"])
        self.assertEqual(E.type_readings(done, done.players[0].active), (EnergyType.LIGHTNING,))
        audited(self, done)

    def test_asleep_lanturn_cannot_use_it(self):
        state = board(lanturn3(sleep=True), opponent=mon(H.CHANSEY))
        rejects(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP", error=IllegalActionError)

    def test_gas_after_use_stops_only_where_the_type_matters(self):
        """せんすいのあとに場にかがくへんかガスが出たら、続くかが決まらない（CE1）。タイプで結果が変わる相手（弱点「水」のヒトカゲ）へのワザは止め、変わらない相手（ラッキー）には止めない。"""
        for opponent, stop in ((H.CHARMANDER, True), (H.CHANSEY, False)):
            with self.subTest(opponent=opponent):
                state = submerged(board(lanturn3(), bench=(mon(H.GRIMER),), hand=(H.MUK,), opponent=mon(opponent, (W,))))
                gassed = evolve(state, H.MUK, target=state.players[0].bench[0])
                lanturn = gassed.players[0].active
                self.assertEqual(E.type_readings(gassed, lanturn), (EnergyType.WATER, EnergyType.LIGHTNING))
                self.assertIsNone(observe(gassed, 1)["players"][0]["active"]["pokemon_type"])
                audited(self, gassed)
                if stop:
                    rejects(self, with_coin_results(gassed, TL), UseAttack(0, 0), CE1)
                else:
                    done = apply_kernel(with_coin_results(gassed, TL), UseAttack(0, 0))
                    self.assertEqual([e["amount"] for e in new_events(gassed, done, "damage")], [30])
                    audited(self, done)

    def test_leaving_play_removes_the_record(self):
        """発生源（このカード）が場をはなれたら、変える対象がないので記録を消す（コマンドの終わり。ログ ``target_gone``）。"""
        state = submerged(board(lanturn3(), bench=(mon(H.RATTATA),), hand=(H.SCOOP_UP,), opponent=mon(H.CHANSEY)))
        asking = play(state, H.SCOOP_UP)
        done = answer(asking, (state.players[0].active.pokemon_id,))
        self.assertEqual(done.color_effects, ())
        self.assertIn("target_gone", [e["reason"] for e in new_events(state, done, "color_effect_removed")])
        audited(self, done)



# ---------------------------------------------------------------- 5.3 節: ［エナジーコンバーター］（ポリゴン2 neo3-051）


class EnergyConverterTest(unittest.TestCase):

    def test_choose_a_color_and_the_card_provides_it_until_the_end_of_the_turn(self):
        state = board(porygon2(), bench=(mon(H.MAGMAR, (F, W)),), opponent=mon(H.CHANSEY))
        magmar = state.players[0].bench[0]
        asking = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, energy=magmar.energy[1], source=magmar.pokemon_id))
        self.assertEqual((asking.decision.kind, asking.decision.options, asking.decision.player), ("select_color", E.NON_COLORLESS_CHOICES, 0))
        done = answer(asking, (COLOR[EnergyType.FIRE],))
        holder = done.players[0].bench[0]
        self.assertEqual(E.energy_units(done, holder, magmar.energy[1]), (frozenset({EnergyType.FIRE}),))
        self.assertTrue(done.card_def(magmar.energy[1]).is_basic_energy)  # カードの種類・印刷の色は変えない
        self.assertEqual(done.card_def(magmar.energy[1]).provides, EnergyType.WATER)
        self.assertEqual(done.energy_attachments_this_turn, state.energy_attachments_this_turn)  # つけ直しではない
        rejects(self, done, UsePokemonPower(0, done.players[0].active.pokemon_id, 0, energy=magmar.energy[0], source=magmar.pokemon_id), "POWER_ALREADY_USED",
                error=IllegalActionError)
        audited(self, done)
        ended = apply_kernel(done, EndTurn(0))
        self.assertEqual(ended.color_effects, ())
        self.assertEqual(E.energy_units(ended, ended.players[0].bench[0], magmar.energy[1]), (frozenset({EnergyType.WATER}),))
        audited(self, ended)

    def test_converted_card_pays_the_new_color(self):
        """ブーバーのほのおパンチ（炎炎）を、「炎」にした水エネルギーカードと炎エネルギーカードで払える。変えなければ払えない。"""
        state = board(mon(H.MAGMAR, (F, W)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
        rejects(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY", error=IllegalActionError)
        magmar = state.players[0].active
        changed = convert(state, magmar, magmar.energy[1], EnergyType.FIRE, user=state.players[0].bench[0])
        done = apply_kernel(changed, UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in new_events(changed, done, "damage")], [30])
        audited(self, done)

    def test_card_level_text_stops_with_a_converted_card(self):
        """ヒトカゲのひのこ（「炎」エネルギーカードを 1 枚トラッシュ）は、「炎」にした水エネルギーカードがカードとしての「炎」かが決まらない（CE3）。"""
        state = board(mon(H.CHARMANDER, (W, W)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
        charmander = state.players[0].active
        changed = convert(state, charmander, charmander.energy[0], EnergyType.FIRE, user=state.players[0].bench[0])
        rejects(self, changed, UseAttack(0, 1), CE3)

    def test_rejections(self):
        state = board(porygon2((W, H.DOUBLE_COLORLESS_ENERGY)), bench=(mon(H.MAGMAR, (F,)),), opponent=mon(H.CHANSEY, (W,)))
        user, magmar, chansey = state.players[0].active, state.players[0].bench[0], state.players[1].active
        cases = (
            ({"energy": user.energy[1], "source": user.pokemon_id}, "NOT_BASIC_ENERGY"),
            ({"energy": chansey.energy[0], "source": chansey.pokemon_id}, "SOURCE_NOT_YOURS"),
            ({"energy": user.energy[0], "source": magmar.pokemon_id}, "ENERGY_NOT_ATTACHED"),
            ({"energy": user.energy[0], "source": user.pokemon_id, "target": magmar.pokemon_id}, "POWER_CHOICE_NOT_USED"),
            ({"energy": user.energy[0]}, "POWER_CHOICE_MISSING"),
        )
        for choices, code in cases:
            with self.subTest(code=code):
                rejects(self, state, UsePokemonPower(0, user.pokemon_id, 0, **choices), code, error=IllegalActionError)
        asleep = board(porygon2(sleep=True), opponent=mon(H.CHANSEY))
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0, energy=asleep.players[0].active.energy[0],
                                                source=asleep.players[0].active.pokemon_id), "POKEMON_ASLEEP", error=IllegalActionError)
        gas = board(porygon2(), opponent=mon(H.CHANSEY), opponent_bench=(muk(),))
        rejects(self, gas, UsePokemonPower(0, gas.players[0].active.pokemon_id, 0, energy=gas.players[0].active.energy[0],
                                              source=gas.players[0].active.pokemon_id), "POWER_SUPPRESSED", error=IllegalActionError)

    def test_confusion_ends_the_effect(self):
        """エリカのラフレシアの［ぼうぎょかふん］でポリゴン2がこんらん状態になったら、効果も消える（ログ ``special_condition``）。"""
        state = board(porygon2((W, W, W, W)), opponent=erikas_vileplume())
        user = state.players[0].active
        changed = convert(state, user, user.energy[3], EnergyType.FIRE)
        done = apply_kernel(with_coin_results(changed, HD, TL), UseAttack(0, 0))
        self.assertTrue(done.players[0].active.conditions.confused)
        self.assertEqual(done.color_effects, ())
        self.assertEqual([e["reason"] for e in new_events(changed, done, "color_effect_removed")], ["special_condition"])
        audited(self, done)

    def test_gas_after_use_stops_only_where_the_color_matters(self):
        """変えたあとに場にかがくへんかガスが出たら、続くかが決まらない（CE1）。払えるかが変わるほのおパンチは止め、どちらの読み方でも払えるなら止めない。"""
        for energy, stop in (((F, W), True), ((F, F, W), False)):
            with self.subTest(energy=energy):
                state = board(mon(H.MAGMAR, energy), bench=(porygon2((W,)), mon(H.GRIMER)), hand=(H.MUK,), opponent=mon(H.CHANSEY))
                magmar = state.players[0].active
                changed = convert(state, magmar, magmar.energy[-1], EnergyType.FIRE, user=state.players[0].bench[0])
                gassed = evolve(changed, H.MUK, target=changed.players[0].bench[1])
                audited(self, gassed)
                if stop:
                    rejects(self, gassed, UseAttack(0, 0), CE1)
                else:
                    done = apply_kernel(gassed, UseAttack(0, 0))
                    self.assertEqual([e["amount"] for e in new_events(gassed, done, "damage")], [30])

    def test_photosynthesis_and_converter_to_another_color_is_ce2(self):
        """こうごうせい（すべて「草」）のエリカのナゾノクサのカードを「炎」にすると、どちらの色かが決まらない（CE2）。どくのこな（草草）を払えるかが変わるので止める。
        同じ「草」にするなら読み方は 1 つで、止めない。"""
        for color, stop in ((EnergyType.FIRE, True), (EnergyType.GRASS, False)):
            with self.subTest(color=color):
                state = board(mon(H.ERIKAS_ODDISH_GD4, (W, W)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
                oddish = state.players[0].active
                changed = convert(state, oddish, oddish.energy[0], color, user=state.players[0].bench[0])
                audited(self, changed)
                if stop:
                    rejects(self, with_coin_results(changed, TL), UseAttack(0, 0), CE2)
                else:
                    done = apply_kernel(with_coin_results(changed, TL), UseAttack(0, 0))
                    self.assertEqual([e["amount"] for e in new_events(changed, done, "damage")], [20])

    def test_reattached_card_is_ce1(self):
        """色を変えたカードが場をはなれ（「にげる」でトラッシュ）、同じ番にもう一度ついたら、続くかが決まらない（CE1）。払えるかが変わるほのおパンチを止める。"""
        state = board(porygon2((W,)), bench=(mon(H.MAGMAR, (F,)),), hand=(H.ENERGY_RETRIEVAL, H.POTION), opponent=mon(H.CHANSEY))
        user = state.players[0].active
        uid = user.energy[0]
        changed = convert(state, user, uid, EnergyType.FIRE)
        retreated = apply_kernel(changed, Retreat(0, (uid,), changed.players[0].bench[0].card))
        self.assertEqual(retreated.color_effects[0].left_play, True)
        discard = play(retreated, H.ENERGY_RETRIEVAL)
        potion = next(u for u in discard.players[0].hand if discard.cards[u].card_id == H.POTION)
        retrieve = answer(discard, (potion,))
        back = answer(retrieve, (uid,))
        from kyuura_engine import AttachEnergy

        attached = apply_kernel(back, AttachEnergy(0, uid, back.players[0].active.card))
        self.assertEqual(len(E.card_color_readings(attached, attached.players[0].active, uid)), 2)
        audited(self, attached)
        rejects(self, attached, UseAttack(0, 0), CE1)


# ---------------------------------------------------------------- 5.4 節: こうごうせい（エリカのナゾノクサ GD4-001）


class PhotosynthesisTest(unittest.TestCase):

    def test_every_energy_counts_as_grass(self):
        """水・炎エネルギーカード（「草」2 個）・無色2個エネルギー（「草」2 個）で、どくのこな（草草）を払える。カードの種類・印刷の色は変えない。"""
        for energy in ((W, F), (H.DOUBLE_COLORLESS_ENERGY,)):
            with self.subTest(energy=energy):
                state = board(mon(H.ERIKAS_ODDISH_GD4, energy), opponent=mon(H.CHANSEY))
                oddish = state.players[0].active
                self.assertTrue(all(unit == frozenset({EnergyType.GRASS}) for unit in E.attached_units(state, oddish)))
                done = apply_kernel(with_coin_results(state, HD), UseAttack(0, 0))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [20])
                self.assertIsNotNone(done.players[1].active.conditions.poison)
                audited(self, done)

    def test_special_conditions_do_not_stop_it_but_gas_does(self):
        asleep = board(mon(H.ERIKAS_ODDISH_GD4, (W,), sleep=True), opponent=mon(H.CHANSEY))
        self.assertEqual(E.attached_units(asleep, asleep.players[0].active), [frozenset({EnergyType.GRASS})])
        gas = board(mon(H.ERIKAS_ODDISH_GD4, (W, F)), opponent=mon(H.CHANSEY), opponent_bench=(muk(),))
        self.assertEqual(E.attached_units(gas, gas.players[0].active), [frozenset({EnergyType.WATER}), frozenset({EnergyType.FIRE})])
        rejects(self, gas, UseAttack(0, 0), "INSUFFICIENT_ENERGY", error=IllegalActionError)

    def test_only_cards_attached_to_this_pokemon(self):
        """ほかのポケモン（ベンチのナゾノクサでない）についているカードは「草」にならない。"""
        state = board(mon(H.MAGMAR, (W, W)), bench=(mon(H.ERIKAS_ODDISH_GD4),), opponent=mon(H.CHANSEY))
        self.assertEqual(E.attached_units(state, state.players[0].active), [frozenset({EnergyType.WATER})] * 2)

    def test_energy_trans_card_level_stops(self):
        """フシギバナのエナジートランス（「草」エネルギーカードをつけかえる）で、こうごうせいで「草」になった水エネルギーカードを選ぶと止める（CE3）。本当の草エネルギーカードは動かせる。"""
        venusaur = stage2(H.VENUSAUR, line=(H.BULBASAUR, H.IVYSAUR))
        state = board(venusaur, bench=(mon(H.ERIKAS_ODDISH_GD4, (W, G)),), opponent=mon(H.CHANSEY))
        oddish = state.players[0].bench[0]
        user = state.players[0].active
        rejects(self, state, UsePokemonPower(0, user.pokemon_id, 0, energy=oddish.energy[0], source=oddish.pokemon_id, target=user.pokemon_id), CE3)
        done = apply_kernel(state, UsePokemonPower(0, user.pokemon_id, 0, energy=oddish.energy[1], source=oddish.pokemon_id, target=user.pokemon_id))
        self.assertEqual(done.players[0].active.energy, [oddish.energy[1]])
        audited(self, done)


    def test_ecogym_colorless_check_is_ce3(self):
        """エコロジムの「「無色」以外の「エネルギーカード」」: こうごうせいで「草」になった無色2個エネルギーが当たるかが決まらない（CE3）。相手のエネルギー・リムーブで
        そのカードを選ぶ答えだけを受け付けない。水エネルギーカードはどちらの読み方でも「無色」以外なので、手札にもどる。"""
        from kyuura_engine import ResolveDecision

        state = board(mon(H.CHANSEY), hand=(H.ECOGYM, H.ENERGY_REMOVAL), opponent=mon(H.ERIKAS_ODDISH_GD4, (H.DOUBLE_COLORLESS_ENERGY, W)))
        choosing = play(play(state, H.ECOGYM), H.ENERGY_REMOVAL)
        dce, water = choosing.players[1].active.energy
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (dce,)), CE3)
        done = answer(choosing, (water,))
        self.assertIn(water, done.players[1].hand)
        audited(self, done)

# ---------------------------------------------------------------- 5.5 節: ［でんじりょく］（レアコイル neo3-045）


class MagneticForceTest(unittest.TestCase):

    def test_move_energy_among_named_pokemon(self):
        state = board(magneton(), bench=(mon(H.MAGNEMITE, (W, F)), mon(H.DARK_MAGNETON, played_turn=2, evolved_from=H.MAGNEMITE, evolved_turn=3)),
                      opponent=mon(H.CHANSEY))
        user, coil, dark = state.players[0].active, state.players[0].bench[0], state.players[0].bench[1]
        once = apply_kernel(state, UsePokemonPower(0, user.pokemon_id, 0, energy=coil.energy[0], source=coil.pokemon_id, target=dark.pokemon_id))
        twice = apply_kernel(once, UsePokemonPower(0, user.pokemon_id, 0, energy=coil.energy[1], source=coil.pokemon_id, target=user.pokemon_id))
        self.assertEqual((twice.players[0].bench[0].energy, twice.players[0].bench[1].energy), ([], [coil.energy[0]]))
        self.assertIn(coil.energy[1], twice.players[0].active.energy)
        self.assertEqual(twice.energy_attachments_this_turn, state.energy_attachments_this_turn)
        self.assertEqual([e["energy"] for e in new_events(state, twice, "move_energy")], list(coil.energy))
        audited(self, twice)

    def test_rejections(self):
        state = board(magneton(), bench=(mon(H.LT_SURGES_MAGNEMITE, (W,)), mon(H.MAGNEMITE, (W,))), opponent=mon(H.CHANSEY))
        user, surge, coil = state.players[0].active, state.players[0].bench[0], state.players[0].bench[1]
        cases = (
            ({"energy": surge.energy[0], "source": surge.pokemon_id, "target": user.pokemon_id}, "SOURCE_NOT_NAMED"),  # 「マチスのコイル」は名前が違う
            ({"energy": coil.energy[0], "source": coil.pokemon_id, "target": surge.pokemon_id}, "TARGET_NOT_NAMED"),
            ({"energy": coil.energy[0], "source": coil.pokemon_id, "target": coil.pokemon_id}, "SAME_POKEMON"),
            ({"energy": user.energy[0], "source": coil.pokemon_id, "target": user.pokemon_id}, "ENERGY_NOT_ATTACHED"),
            ({"energy": coil.energy[0], "source": coil.pokemon_id}, "POWER_CHOICE_MISSING"),
        )
        for choices, code in cases:
            with self.subTest(code=code):
                rejects(self, state, UsePokemonPower(0, user.pokemon_id, 0, **choices), code, error=IllegalActionError)
        asleep = board(magneton(sleep=True), bench=(mon(H.MAGNEMITE, (W,)),), opponent=mon(H.CHANSEY))
        coil = asleep.players[0].bench[0]
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0, energy=coil.energy[0], source=coil.pokemon_id,
                                                 target=asleep.players[0].active.pokemon_id), "POKEMON_ASLEEP", error=IllegalActionError)

    def test_crystal_beam_target_is_cb1(self):
        """カスミのメノクラゲのクリスタルビームを受けたポケモンへのつけ替えは、v0.59 の CB1。"""
        state = board(mon(H.MAGNEMITE, (W,)), bench=(magneton(),), opponent=mon(H.MISTYS_TENTACOOL, (W, W)), current=1, turn=8)
        mine = apply_kernel(with_coin_results(state, HD), UseAttack(1, 0))  # ワザのあと番が終わる
        user, coil = mine.players[0].bench[0], mine.players[0].active
        rejects(self, mine, UsePokemonPower(0, user.pokemon_id, 0, energy=user.energy[0], source=user.pokemon_id, target=coil.pokemon_id),
                "UNRESOLVED_ATTACH_BLOCK_SCOPE")

    def test_converted_card_keeps_its_color_when_moved(self):
        """［エナジーコンバーター］で色を変えたカードは、つけ替えても効果が続く（カードを追う）。"""
        state = board(magneton((L, L, W)), bench=(porygon2((W,)), mon(H.MAGNEMITE)), opponent=mon(H.CHANSEY))
        user = state.players[0].active
        uid = user.energy[2]
        changed = convert(state, user, uid, EnergyType.FIRE, user=state.players[0].bench[0])
        moved = apply_kernel(changed, UsePokemonPower(0, user.pokemon_id, 0, energy=uid, source=user.pokemon_id, target=changed.players[0].bench[1].pokemon_id))
        self.assertEqual(E.energy_units(moved, moved.players[0].bench[1], uid), (frozenset({EnergyType.FIRE}),))
        audited(self, moved)


# ---------------------------------------------------------------- 6 章: 色を選ぶ・数えるワザ


class CoreStreamTest(unittest.TestCase):

    def test_hits_pokemon_with_energy_of_the_chosen_color(self):
        """選んだ色の「エネルギー」のついている相手のポケモン全員に 20（弱点・抵抗力に関係なく）。こうごうせいのエリカのナゾノクサの水エネルギーカードは「草」エネルギー。"""
        state = board(stage1(H.STARMIE_NEO3, (P, P, W), base=H.STARYU), opponent=mon(H.MR_MIME, (P,)),
                      opponent_bench=(mon(H.RATTATA, (W,)), mon(H.ERIKAS_ODDISH_GD4, (W,)), mon(H.RATTATA, (P,))))
        asking = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((asking.decision.kind, asking.decision.options), ("select_color", E.NON_COLORLESS_CHOICES))
        them = state.players[1]
        for color, hit in ((EnergyType.PSYCHIC, [them.active, them.bench[2]]), (EnergyType.GRASS, [them.bench[1]]), (EnergyType.WATER, [them.bench[0]]),
                           (EnergyType.FIRE, [])):
            with self.subTest(color=color):
                done = answer(asking, (COLOR[color],))
                self.assertEqual(damages(asking, done), [(p.card, 20) for p in hit])
                audited(self, done)


class RainbowWaveTest(unittest.TestCase):

    def test_choose_from_own_basic_energy_card_colors(self):
        """選べる色は自分についている基本エネルギーカードの色（無色2個エネルギーは入れない）。相手と控えの、そのタイプのポケモン全員に 20（弱点・抵抗力に関係なく）。"""
        state = board(mon(H.MEW_SI, (P, F, H.DOUBLE_COLORLESS_ENERGY)), opponent=mon(H.CHARMANDER), opponent_bench=(mon(H.SQUIRTLE), mon(H.CHARMANDER)))
        asking = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(asking.decision.options, tuple(sorted((COLOR[EnergyType.PSYCHIC], COLOR[EnergyType.FIRE]))))
        done = answer(asking, (COLOR[EnergyType.FIRE],))
        them = state.players[1]
        self.assertEqual(damages(asking, done), [(them.active.card, 20), (them.bench[1].card, 20)])
        audited(self, done)

    def test_targets_use_the_current_type(self):
        """相手のモルフォンが前の番に［へんしょく］で「炎」にした色は続くかが決まらない（VS1）。選べる色に炎・草があれば宣言の前に止め、なければ止めない。"""
        venomoth = mon(H.VENOMOTH, played_turn=2, evolved_from=H.VENONAT, evolved_turn=4)
        for energy, stop in (((P, F), True), ((P, W), False)):
            with self.subTest(energy=energy):
                state = board(mon(H.MEW_SI, energy), opponent=venomoth, opponent_bench=(mon(H.CHARMANDER),), current=1, turn=8)
                asking = apply_kernel(state, UsePokemonPower(1, state.players[1].active.pokemon_id, 0))
                shifted = apply_kernel(answer(asking, (COLOR[EnergyType.FIRE],)), EndTurn(1))
                self.assertEqual(E.type_readings(shifted, shifted.players[1].active), (EnergyType.FIRE, EnergyType.GRASS))
                if stop:
                    rejects(self, shifted, UseAttack(0, 0), "UNRESOLVED_SHIFT_COLOR_DURATION")
                else:
                    done = answer(apply_kernel(shifted, UseAttack(0, 0)), (COLOR[EnergyType.WATER],))
                    self.assertEqual(damages(shifted, done), [])
                    audited(self, done)

    def test_rainbow_and_converted_cards_stop(self):
        """レインボーエネルギー（「基本エネルギーカード」か。RB3）・「炎」にした水エネルギーカード（カードとしての色。CE3）で選べる色が変わるなら止める。"""
        rainbow = board(mon(H.MEW_SI, (H.RAINBOW_ENERGY,)), opponent=mon(H.CHARMANDER))
        rejects(self, rainbow, UseAttack(0, 0), "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD")
        state = board(mon(H.MEW_SI, (P, W)), bench=(porygon2((W,)),), opponent=mon(H.CHARMANDER))
        mew = state.players[0].active
        changed = convert(state, mew, mew.energy[1], EnergyType.FIRE, user=state.players[0].bench[0])
        rejects(self, changed, UseAttack(0, 0), CE3)


class RainbowBurnTest(unittest.TestCase):

    def test_distinct_printed_colors(self):
        """基本エネルギーカードの色の種類 × 10 を 30 に足す（同じ色が 2 枚でも 10）。無色2個エネルギーは数えない。"""
        for energy, expected in (((W, W, F, L), 60), ((W, F, H.DOUBLE_COLORLESS_ENERGY), 50)):
            with self.subTest(energy=energy):
                state = board(mon(H.HO_OH_PF3, energy), opponent=mon(H.CHANSEY))
                done = apply_kernel(state, UseAttack(0, 0))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [expected])
                audited(self, done)

    def test_stops_only_when_the_count_changes(self):
        rainbow = board(mon(H.HO_OH_PF3, (W, F, L, H.RAINBOW_ENERGY)), opponent=mon(H.CHANSEY))
        rejects(self, rainbow, UseAttack(0, 0), "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD")
        for color, stop in ((EnergyType.FIRE, True), (EnergyType.GRASS, False)):
            with self.subTest(color=color):
                state = board(mon(H.HO_OH_PF3, (W, F, L, L)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
                ho_oh = state.players[0].active
                changed = convert(state, ho_oh, ho_oh.energy[0], color, user=state.players[0].bench[0])
                if stop:
                    rejects(self, changed, UseAttack(0, 0), CE3)  # 水 → 炎 で 3 色が 2 色になりうる
                else:
                    done = apply_kernel(changed, UseAttack(0, 0))  # 水 → 草 でも 3 色
                    self.assertEqual([e["amount"] for e in new_events(changed, done, "damage")], [60])


class OtherAttacksTest(unittest.TestCase):

    def test_plasma_attaches_a_lightning_energy_card_from_the_discard(self):
        for discard, attached in (((L, W), 1), ((W,), 0)):
            with self.subTest(discard=discard):
                state = board(magneton((L, L, W)), discard=discard, opponent=mon(H.CHANSEY))
                done = apply_kernel(state, UseAttack(0, 0))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [30])
                if attached:
                    self.assertEqual(done.decision.kind, "attach_from_discard")
                    self.assertEqual([done.cards[u].card_id for u in done.decision.options], [L])  # 「雷」エネルギーカードだけ
                    done = answer(done, done.decision.options)
                self.assertEqual(len(done.players[0].active.energy), 3 + attached)
                audited(self, done)

    def test_delta_beam_chooses_one_of_three_conditions(self):
        state = board(porygon2(), opponent=mon(H.CHANSEY))
        asking = apply_kernel(with_coin_results(state, HD), UseAttack(0, 0))
        self.assertEqual(len(asking.decision.options), 3)
        found = []
        for option in asking.decision.options:
            done = answer(asking, (option,))
            exclusive = done.players[1].active.conditions.exclusive
            found.append(type(exclusive).__name__)
            audited(self, done)
        self.assertEqual(found, ["Asleep", "Paralyzed", "Confused"])
        tails = apply_kernel(with_coin_results(state, TL), UseAttack(0, 0))
        self.assertIsNone(tails.decision)
        self.assertIsNone(tails.players[1].active.conditions.exclusive)

    def test_three_d_attack(self):
        for card, energy, coins, expected in ((H.PORYGON_ES1, (W,), (HD, HD, TL), 20), (H.PORYGON_QSG, (W,), (TL, TL, TL), 0),
                                               (H.COOL_PORYGON, (W, W, W), (HD, HD, HD), 60)):
            with self.subTest(card=card):
                state = board(mon(card, energy), opponent=mon(H.CHANSEY))
                index = 1 if card == H.COOL_PORYGON else 0
                done = apply_kernel(with_coin_results(state, *coins), UseAttack(0, index))
                self.assertEqual([e["amount"] for e in new_events(state, done, "damage")], [expected])
                audited(self, done)


class TextureTest(unittest.TestCase):

    def test_texture_two_may_change_or_not(self):
        state = board(mon(H.PORYGON_ES1, (W, W)), opponent=mon(H.CHANSEY))
        asking = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((asking.decision.min_choices, asking.decision.max_choices), (0, 1))
        declined = answer(asking, ())
        self.assertEqual(E.resistance_of(declined, declined.players[0].active)[0], EnergyType.PSYCHIC)
        self.assertEqual(len(new_events(asking, declined, "color_change_declined")), 1)
        changed = answer(asking, (COLOR[EnergyType.FIRE],))
        self.assertEqual(E.resistance_of(changed, changed.players[0].active), (EnergyType.FIRE, 30))
        audited(self, declined)
        audited(self, changed)

    def test_copied_texture_two_without_resistance(self):
        """カスミのコダック（抵抗力なし）がちょうのうりょくでテクスチャー2を使うと、色を選ぶ答えは PG1。変えないことはできるので、宣言の前には止めない。"""
        from kyuura_engine import ResolveDecision

        state = board(mon(H.MISTYS_PSYDUCK, (P,)), opponent=mon(H.PORYGON_ES1))
        copy = apply_kernel(with_coin_results(state, HD, HD, HD), UseAttack(0, 0))
        self.assertEqual(copy.decision.kind, "select_attack")
        asking = answer(copy, (1,))
        self.assertEqual((asking.decision.kind, asking.decision.min_choices), ("select_color", 0))
        rejects(self, asking, ResolveDecision(0, asking.decision.id, (COLOR[EnergyType.FIRE],)), "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE")
        declined = answer(asking, ())
        self.assertIsNone(E.resistance_of(declined, declined.players[0].active)[0])
        audited(self, declined)

    def test_texture_magic_both_one_or_neither(self):
        state = board(mon(H.COOL_PORYGON, (W, W, W)), opponent=mon(H.CHANSEY))
        for weakness, resistance in ((EnergyType.WATER, EnergyType.FIRE), (EnergyType.WATER, None), (None, EnergyType.FIRE), (None, None)):
            with self.subTest(weakness=weakness, resistance=resistance):
                first = apply_kernel(state, UseAttack(0, 0))
                second = answer(first, () if weakness is None else (COLOR[weakness],))
                done = answer(second, () if resistance is None else (COLOR[resistance],))
                self.assertEqual(E.weakness_of(done, done.players[1].active), weakness or EnergyType.FIGHTING)
                self.assertEqual(E.resistance_of(done, done.players[0].active)[0], resistance or EnergyType.PSYCHIC)
                audited(self, done)

    def test_texture_magic_without_opponent_weakness_and_bad_second_answer(self):
        """相手に弱点がなければ、弱点の部分は何もしない（PG1 にしない）。あとの決定への不正な答えは、前に受け付けた答えを取り消さない。"""
        state = board(mon(H.COOL_PORYGON, (W, W, W)), opponent=mon(H.GASTLY))
        asking = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(len(new_events(state, asking, "persistent_effect_added")), 0)
        self.assertEqual(asking.decision.kind, "select_color")
        self.assertEqual(asking.decision.context_value("target"), asking.players[0].active.pokemon_id)  # 自分の抵抗力の決定だけ
        state = board(mon(H.COOL_PORYGON, (W, W, W)), opponent=mon(H.CHANSEY))
        second = answer(apply_kernel(state, UseAttack(0, 0)), (COLOR[EnergyType.WATER],))
        from kyuura_engine import ResolveDecision

        rejects(self, second, ResolveDecision(0, second.decision.id, (99,)), "INVALID_CHOICE", error=IllegalActionError)
        self.assertEqual(E.weakness_of(second, second.players[1].active), EnergyType.WATER)


# ---------------------------------------------------------------- 2 章: 書き出し（形式 23）・観測


class SerializationTest(unittest.TestCase):

    def test_color_effects_need_format_23(self):
        state = submerged(board(lanturn3(), opponent=mon(H.CHANSEY)))
        self.assertEqual(max(FORMAT_VERSIONS), 23)
        data = state_to_dict(state, format_version=23)
        self.assertEqual([(e["kind"], e["target"], e["color"]) for e in data["color_effects"]], [("pokemon_type", state.players[0].active.pokemon_id, "water")])
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=22)
        plain = board(lanturn3(), opponent=mon(H.CHANSEY))
        self.assertNotIn("color_effects", state_to_dict(plain, format_version=22))

    def test_observation(self):
        state = board(mon(H.MAGMAR, (F, W)), bench=(porygon2((W,)),), opponent=mon(H.CHANSEY))
        magmar = state.players[0].active
        changed = convert(state, magmar, magmar.energy[1], EnergyType.FIRE, user=state.players[0].bench[0])
        for viewer in (0, 1):
            seen = observe(changed, viewer)
            self.assertEqual(seen["players"][0]["active"]["energy_units"], [["fire"], ["fire"]])
            self.assertTrue(seen["players"][0]["active"]["energy_units_determined"])
            self.assertEqual([(e["kind"], e["target"], e["color"]) for e in seen["color_effects"]], [("energy", magmar.energy[1], "fire")])


if __name__ == "__main__":
    unittest.main()
